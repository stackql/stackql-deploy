# cmd/build.py
import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, Dict, Any, List

from ..lib.utils import (
    catch_error_and_exit,
    export_vars,
    run_ext_script,
    get_type,
    print_unicode_box,
    BorderColor
)
from ..lib.config import get_full_context, render_value
from ..lib.templating import get_queries, render_inline_template
from .base import StackQLBase


class ResourceType(Enum):
    """Resource types supported by StackQL provisioner."""
    RESOURCE = 'resource'
    MULTI = 'multi'
    QUERY = 'query'
    COMMAND = 'command'
    SCRIPT = 'script'


@dataclass
class QueryConfig:
    """Configuration for a query execution."""
    query: Optional[str]
    retries: int = 1
    retry_delay: int = 0


@dataclass
class ResourceState:
    """State information for a resource."""
    exists: bool = False
    is_correct_state: bool = False
    exports_result: Optional[Any] = None


@dataclass
class ProvisioningQueries:
    """Container for all provisioning-related queries."""
    create: QueryConfig
    update: QueryConfig
    exists: QueryConfig
    statecheck: QueryConfig
    exports: QueryConfig
    command: Optional[QueryConfig] = None


class StackQLProvisioner(StackQLBase):

    def _extract_query_config(self, resource_queries: Dict, query_type: str) -> QueryConfig:
        """Extract query configuration from resource_queries."""
        query_data = resource_queries.get(query_type, {})
        return QueryConfig(
            query=query_data.get('rendered'),
            retries=query_data.get('options', {}).get('retries', 1),
            retry_delay=query_data.get('options', {}).get('retry_delay', 0)
        )

    def _resolve_create_update_queries(
        self,
        resource_queries: Dict
    ) -> Tuple[QueryConfig, QueryConfig]:
        """Resolve create/update queries, handling createorupdate precedence."""
        createorupdate = self._extract_query_config(resource_queries, 'createorupdate')

        if createorupdate.query:
            # createorupdate supersedes separate create and update queries
            return createorupdate, createorupdate

        create = self._extract_query_config(resource_queries, 'create')
        update = self._extract_query_config(resource_queries, 'update')
        return create, update

    def _evaluate_resource_condition(
        self,
        resource: Dict,
        full_context: Dict
    ) -> bool:
        """Evaluate the 'if' condition for a resource. Returns True if should process."""
        if 'if' not in resource:
            return True

        condition = resource['if']
        try:
            rendered_condition = render_value(self.env, condition, full_context, self.logger)
            condition_result = eval(rendered_condition)
            if not condition_result:
                self.logger.info(
                    f"skipping resource [{resource['name']}] due to condition: {condition}"
                )
            return condition_result
        except Exception as e:
            catch_error_and_exit(
                f"error evaluating condition for resource [{resource['name']}]: {e}",
                self.logger
            )

    def _get_resource_queries(
        self,
        resource: Dict,
        resource_type: str,
        full_context: Dict
    ) -> Tuple[Dict, Optional[str]]:
        """Get resource queries, handling both inline SQL and file-based queries."""
        inline_query = None

        if (resource_type in (ResourceType.COMMAND.value, ResourceType.QUERY.value)
            and 'sql' in resource):
            # Inline SQL specified in the resource
            inline_query = render_inline_template(
                self.env,
                resource["name"],
                resource["sql"],
                full_context,
                self.logger
            )
            return {}, inline_query

        # Load queries from file
        resource_queries = get_queries(
            self.env,
            self.stack_dir,
            'resources',
            resource,
            full_context,
            self.logger
        )
        return resource_queries, inline_query

    def _build_provisioning_queries(
        self,
        resource_queries: Dict,
        resource_type: str
    ) -> ProvisioningQueries:
        """Build all provisioning queries from resource_queries."""
        create_config, update_config = self._resolve_create_update_queries(resource_queries)

        return ProvisioningQueries(
            create=create_config,
            update=update_config,
            exists=self._extract_query_config(resource_queries, 'exists'),
            statecheck=self._extract_query_config(resource_queries, 'statecheck'),
            exports=self._extract_query_config(resource_queries, 'exports')
        )

    def _validate_provisioning_queries(
        self,
        queries: ProvisioningQueries,
        resource_type: str
    ):
        """Validate that required queries are present."""
        if resource_type in (ResourceType.RESOURCE.value, ResourceType.MULTI.value):
            if not queries.create.query:
                catch_error_and_exit(
                    "iql file must include either 'create' or 'createorupdate' anchor.",
                    self.logger
                )

            if not queries.exists.query and not queries.statecheck.query and not queries.exports.query:
                catch_error_and_exit(
                    "iql file must include either 'exists', 'statecheck', or 'exports' anchor.",
                    self.logger
                )

    def _check_with_exports_first(
        self,
        resource: Dict,
        full_context: Dict,
        exports_config: QueryConfig,
        dry_run: bool,
        show_queries: bool
    ) -> Tuple[bool, Optional[Any]]:
        """Try exports query first for optimal single-query validation."""
        self.logger.info(
            f"🔄 trying exports query first for optimal single-query validation "
            f"for [{resource['name']}]"
        )

        is_correct_state, exports_result = self.check_state_using_exports_proxy(
            resource,
            full_context,
            exports_config.query,
            exports_config.retries,
            exports_config.retry_delay,
            dry_run,
            show_queries
        )

        if is_correct_state:
            self.logger.info(
                f"✅ [{resource['name']}] validated successfully with single exports query"
            )
        else:
            self.logger.info(
                f"📋 exports validation failed, falling back to exists check "
                f"for [{resource['name']}]"
            )

        return is_correct_state, exports_result

    def _fallback_to_exists_check(
        self,
        resource: Dict,
        full_context: Dict,
        queries: ProvisioningQueries,
        dry_run: bool,
        show_queries: bool
    ) -> Tuple[bool, bool]:
        """Fallback to traditional exists/statecheck when exports fails or is unavailable."""
        resource_exists = False
        is_correct_state = False

        if queries.exists.query:
            resource_exists = self.check_if_resource_exists(
                False,
                resource,
                full_context,
                queries.exists.query,
                queries.exists.retries,
                queries.exists.retry_delay,
                dry_run,
                show_queries
            )
        elif queries.statecheck.query:
            # statecheck can be used as an exists check fallback
            is_correct_state = self.check_if_resource_is_correct_state(
                False,
                resource,
                full_context,
                queries.statecheck.query,
                queries.statecheck.retries,
                queries.statecheck.retry_delay,
                dry_run,
                show_queries
            )
            resource_exists = is_correct_state

        return resource_exists, is_correct_state

    def _determine_resource_state(
        self,
        resource: Dict,
        full_context: Dict,
        queries: ProvisioningQueries,
        has_createorupdate: bool,
        dry_run: bool,
        show_queries: bool
    ) -> ResourceState:
        """Determine if resource exists and is in correct state."""
        state = ResourceState()

        if has_createorupdate:
            # Skip existence checks for createorupdate queries
            return state

        # OPTIMIZATION: Try exports first if available for happy path
        if queries.exports.query:
            is_valid, exports_result = self._check_with_exports_first(
                resource, full_context, queries.exports, dry_run, show_queries
            )
            state.is_correct_state = is_valid
            state.exists = is_valid
            state.exports_result = exports_result

            # If exports succeeded, we're done
            if is_valid:
                return state

            # Fall back to traditional checks
            state.exists, state.is_correct_state = self._fallback_to_exists_check(
                resource, full_context, queries, dry_run, show_queries
            )
            # Reset is_correct_state since we need to re-validate after create/update
            state.is_correct_state = False
            state.exports_result = None  # Clear since validation failed

        elif queries.exists.query:
            # Traditional path: use exists query
            state.exists = self.check_if_resource_exists(
                False,
                resource,
                full_context,
                queries.exists.query,
                queries.exists.retries,
                queries.exists.retry_delay,
                dry_run,
                show_queries
            )

        elif queries.statecheck.query:
            # Use statecheck as exists check
            state.is_correct_state = self.check_if_resource_is_correct_state(
                False,
                resource,
                full_context,
                queries.statecheck.query,
                queries.statecheck.retries,
                queries.statecheck.retry_delay,
                dry_run,
                show_queries
            )
            state.exists = state.is_correct_state

        return state

    def _perform_state_validation(
        self,
        resource: Dict,
        full_context: Dict,
        queries: ProvisioningQueries,
        state: ResourceState,
        dry_run: bool,
        show_queries: bool
    ) -> ResourceState:
        """Perform state validation if resource exists but state hasn't been checked."""
        if not state.exists or state.is_correct_state or state.exports_result is not None:
            return state

        # Check if skip_validation is set
        if resource.get('skip_validation', False):
            self.logger.info(
                f"skipping validation for [{resource['name']}] as skip_validation is set to true."
            )
            state.is_correct_state = True
            return state

        # Run statecheck or exports as proxy
        if queries.statecheck.query:
            state.is_correct_state = self.check_if_resource_is_correct_state(
                state.is_correct_state,
                resource,
                full_context,
                queries.statecheck.query,
                queries.statecheck.retries,
                queries.statecheck.retry_delay,
                dry_run,
                show_queries
            )
        elif queries.exports.query:
            self.logger.info(
                f"🔄 using exports query as proxy for statecheck for [{resource['name']}]"
            )
            state.is_correct_state, _ = self.check_state_using_exports_proxy(
                resource,
                full_context,
                queries.exports.query,
                queries.exports.retries,
                queries.exports.retry_delay,
                dry_run,
                show_queries
            )

        return state

    def _provision_resource(
        self,
        resource: Dict,
        full_context: Dict,
        queries: ProvisioningQueries,
        state: ResourceState,
        resource_type: str,
        dry_run: bool,
        show_queries: bool
    ) -> Tuple[ResourceState, bool]:
        """Create or update resource based on its state."""
        ignore_errors = resource_type == ResourceType.MULTI.value
        is_created_or_updated = False

        # Create resource if it doesn't exist
        if not state.exists:
            is_created_or_updated = self.create_resource(
                is_created_or_updated,
                resource,
                full_context,
                queries.create.query,
                queries.create.retries,
                queries.create.retry_delay,
                dry_run,
                show_queries,
                ignore_errors
            )

        # Update resource if it exists but is not in correct state
        elif not state.is_correct_state:
            is_created_or_updated = self.update_resource(
                is_created_or_updated,
                resource,
                full_context,
                queries.update.query,
                queries.update.retries,
                queries.update.retry_delay,
                dry_run,
                show_queries,
                ignore_errors
            )

        return state, is_created_or_updated

    def _post_deploy_validation(
        self,
        resource: Dict,
        full_context: Dict,
        queries: ProvisioningQueries,
        state: ResourceState,
        was_deployed: bool,
        dry_run: bool,
        show_queries: bool
    ) -> ResourceState:
        """Validate resource state after deployment."""
        if not was_deployed:
            return state

        if queries.statecheck.query:
            state.is_correct_state = self.check_if_resource_is_correct_state(
                state.is_correct_state,
                resource,
                full_context,
                queries.statecheck.query,
                queries.statecheck.retries,
                queries.statecheck.retry_delay,
                dry_run,
                show_queries,
            )
        elif queries.exports.query:
            self.logger.info(
                f"🔄 using exports query as proxy for post-deploy statecheck "
                f"for [{resource['name']}]"
            )
            state.is_correct_state, _ = self.check_state_using_exports_proxy(
                resource,
                full_context,
                queries.exports.query,
                queries.exports.retries,
                queries.exports.retry_delay,
                dry_run,
                show_queries
            )

        # Verify deployment succeeded
        if not state.is_correct_state and not dry_run:
            catch_error_and_exit(
                f"❌ deployment failed for {resource['name']} after post-deploy checks.",
                self.logger
            )

        return state

    def _handle_resource_provisioning(
        self,
        resource: Dict,
        full_context: Dict,
        queries: ProvisioningQueries,
        dry_run: bool,
        show_queries: bool
    ):
        """Handle provisioning for resource and multi type resources."""
        has_createorupdate = queries.create.query == queries.update.query

        # Determine initial resource state
        state = self._determine_resource_state(
            resource, full_context, queries, has_createorupdate, dry_run, show_queries
        )

        # Perform state validation if needed
        state = self._perform_state_validation(
            resource, full_context, queries, state, dry_run, show_queries
        )

        # Provision resource (create or update)
        resource_type = get_type(resource, self.logger)
        state, was_deployed = self._provision_resource(
            resource, full_context, queries, state, resource_type, dry_run, show_queries
        )

        # Post-deploy validation
        state = self._post_deploy_validation(
            resource, full_context, queries, state, was_deployed, dry_run, show_queries
        )

        return state

    def _handle_command_resource(
        self,
        resource: Dict,
        resource_queries: Dict,
        inline_query: Optional[str],
        dry_run: bool,
        show_queries: bool
    ):
        """Handle command type resources."""
        if inline_query:
            command_config = QueryConfig(query=inline_query, retries=1, retry_delay=0)
        else:
            command_config = self._extract_query_config(resource_queries, 'command')

        if not command_config.query:
            error_msg = (
                "'sql' should be defined in the resource or the 'command' anchor "
                "needs to be supplied in the corresponding iql file for command "
                "type resources."
            )
            catch_error_and_exit(error_msg, self.logger)

        self.run_command(
            command_config.query,
            command_config.retries,
            command_config.retry_delay,
            dry_run,
            show_queries
        )

    def _handle_query_resource(
        self,
        resource: Dict,
        queries: ProvisioningQueries,
        inline_query: Optional[str]
    ):
        """Validate and prepare query type resources."""
        if not queries.exports.query:
            if inline_query:
                queries.exports = QueryConfig(query=inline_query, retries=1, retry_delay=0)
            else:
                catch_error_and_exit(
                    "inline sql must be supplied or an iql file must be present with an "
                    "'exports' anchor for query type resources.",
                    self.logger
                )

    def _handle_exports(
        self,
        resource: Dict,
        full_context: Dict,
        queries: ProvisioningQueries,
        state: Optional[ResourceState],
        resource_type: str,
        dry_run: bool,
        show_queries: bool
    ):
        """Handle exports for resources."""
        if not queries.exports.query:
            return

        # Reuse exports result if we already ran it as a proxy
        if (state and state.exports_result is not None
            and resource_type in (ResourceType.RESOURCE.value, ResourceType.MULTI.value)):
            self.logger.info(f"📦 reusing exports result from proxy for [{resource['name']}]...")
            expected_exports = resource.get('exports', [])
            if len(expected_exports) > 0:
                self.process_exports_from_result(
                    resource, state.exports_result, expected_exports
                )
        else:
            # Run exports normally
            self.process_exports(
                resource,
                full_context,
                queries.exports.query,
                queries.exports.retries,
                queries.exports.retry_delay,
                dry_run,
                show_queries
            )

    def _process_resource(
        self,
        resource: Dict,
        dry_run: bool,
        show_queries: bool
    ):
        """Process a single resource."""
        print_unicode_box(f"Processing resource: [{resource['name']}]", BorderColor.BLUE)

        resource_type = get_type(resource, self.logger)
        self.logger.info(f"processing resource [{resource['name']}], type: {resource_type}")

        # Get full context
        full_context = get_full_context(self.env, self.global_context, resource, self.logger)

        # Evaluate condition
        if not self._evaluate_resource_condition(resource, full_context):
            return

        # Handle script resources
        if resource_type == ResourceType.SCRIPT.value:
            self.process_script_resource(resource, dry_run, full_context)
            return

        # Get resource queries
        resource_queries, inline_query = self._get_resource_queries(
            resource, resource_type, full_context
        )

        # Build provisioning queries
        queries = self._build_provisioning_queries(resource_queries, resource_type)

        # Handle query type resources
        if resource_type == ResourceType.QUERY.value:
            self._handle_query_resource(resource, queries, inline_query)

        # Validate provisioning queries
        if resource_type in (ResourceType.RESOURCE.value, ResourceType.MULTI.value):
            self._validate_provisioning_queries(queries, resource_type)

        # Process based on resource type
        state = None
        if resource_type in (ResourceType.RESOURCE.value, ResourceType.MULTI.value):
            state = self._handle_resource_provisioning(
                resource, full_context, queries, dry_run, show_queries
            )
        elif resource_type == ResourceType.COMMAND.value:
            self._handle_command_resource(
                resource, resource_queries, inline_query, dry_run, show_queries
            )

        # Handle exports
        self._handle_exports(
            resource, full_context, queries, state, resource_type, dry_run, show_queries
        )

        # Log success
        if not dry_run:
            if resource_type == ResourceType.RESOURCE.value:
                self.logger.info(f"✅ successfully deployed {resource['name']}")
            elif resource_type == ResourceType.QUERY.value:
                self.logger.info(
                    f"✅ successfully exported variables for query in {resource['name']}"
                )

    def process_script_resource(self, resource, dry_run, full_context):
        """Process script type resources."""
        self.logger.info(f"running script for {resource['name']}...")
        script_template = resource.get('run', None)
        if not script_template:
            catch_error_and_exit("script resource must include 'run' key", self.logger)

        script = self.env.from_string(script_template).render(full_context)

        if dry_run:
            dry_run_script = script.replace('""', '"<evaluated>"')
            self.logger.info(f"dry run script for [{resource['name']}]:\n\n{dry_run_script}\n")
        else:
            self.logger.info(f"running script for [{resource['name']}]...")
            try:
                ret_vars = run_ext_script(script, self.logger, resource.get('exports', None))
                if resource.get('exports', None):
                    self.logger.info(f"exported variables from script: {ret_vars}")
                    export_vars(
                        self, resource, ret_vars,
                        resource.get('exports', []),
                        resource.get('protected', [])
                    )
            except Exception as e:
                catch_error_and_exit(f"script failed: {e}", self.logger)

    def run(self, dry_run, show_queries, on_failure, output_file=None):
        """Run the provisioning process for all resources."""
        start_time = datetime.datetime.now()

        self.logger.info(
            f"deploying [{self.stack_name}] in [{self.stack_env}] environment "
            f"{'(dry run)' if dry_run else ''}"
        )

        for resource in self.manifest.get('resources', []):
            self._process_resource(resource, dry_run, show_queries)

        elapsed_time = datetime.datetime.now() - start_time
        self.logger.info(f"deployment completed in {elapsed_time}")

        # Process stack-level exports after all resources are deployed
        self.process_stack_exports(dry_run, output_file, elapsed_time)
