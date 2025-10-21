# cmd/teardown.py
import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Tuple

from ..lib.utils import (
    catch_error_and_exit,
    get_type,
    print_unicode_box,
    BorderColor
)
from ..lib.config import get_full_context, render_value
from ..lib.templating import get_queries, render_inline_template
from .base import StackQLBase


class ResourceType(Enum):
    """Resource types supported by StackQL de-provisioner."""
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
class TeardownQueries:
    """Container for teardown-related queries."""
    exists: QueryConfig
    delete: QueryConfig
    postdelete_exists_retries: int = 10
    postdelete_exists_retry_delay: int = 5


class StackQLDeProvisioner(StackQLBase):

    def _extract_query_config(self, resource_queries: Dict, query_type: str) -> QueryConfig:
        """Extract query configuration from resource_queries."""
        query_data = resource_queries.get(query_type, {})
        return QueryConfig(
            query=query_data.get('rendered'),
            retries=query_data.get('options', {}).get('retries', 1),
            retry_delay=query_data.get('options', {}).get('retry_delay', 0)
        )

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

    def _get_exports_query(
        self,
        resource: Dict,
        resource_type: str,
        full_context: Dict
    ) -> QueryConfig:
        """Get exports query configuration for a resource."""
        if resource_type == ResourceType.QUERY.value and 'sql' in resource:
            # Inline SQL specified in the resource
            exports_query = render_inline_template(
                self.env,
                resource["name"],
                resource["sql"],
                full_context,
                self.logger
            )
            return QueryConfig(query=exports_query, retries=1, retry_delay=0)

        # Load queries from file
        resource_queries = get_queries(
            self.env,
            self.stack_dir,
            'resources',
            resource,
            full_context,
            self.logger
        )
        return self._extract_query_config(resource_queries, 'exports')

    def _collect_resource_exports(
        self,
        resource: Dict,
        show_queries: bool,
        dry_run: bool
    ):
        """Collect exports for a single resource."""
        resource_type = get_type(resource, self.logger)
        self.logger.info(f"getting exports for resource [{resource['name']}]")

        # Skip command resources
        if resource_type == ResourceType.COMMAND.value:
            return

        # Get full context
        full_context = get_full_context(self.env, self.global_context, resource, self.logger)

        # Get exports query
        exports_config = self._get_exports_query(resource, resource_type, full_context)

        if exports_config.query:
            self.process_exports(
                resource,
                full_context,
                exports_config.query,
                exports_config.retries,
                exports_config.retry_delay,
                dry_run,
                show_queries,
                ignore_missing_exports=True
            )

    def _build_teardown_queries(self, resource_queries: Dict) -> TeardownQueries:
        """Build teardown queries from resource_queries."""
        exists = self._extract_query_config(resource_queries, 'exists')
        delete = self._extract_query_config(resource_queries, 'delete')

        # If no exists query, try using statecheck as fallback
        if not exists.query:
            self.logger.info(
                f"exists query not defined, trying to use statecheck query as exists query."
            )
            exists = self._extract_query_config(resource_queries, 'statecheck')

        # Get postdelete retry configuration
        if resource_queries.get('exists', {}).get('rendered'):
            # Use exists query options
            postdelete_retries = resource_queries.get('exists', {}).get(
                'options', {}
            ).get('postdelete_retries', 10)
            postdelete_retry_delay = resource_queries.get('exists', {}).get(
                'options', {}
            ).get('postdelete_retry_delay', 5)
        else:
            # Use statecheck query options
            postdelete_retries = resource_queries.get('statecheck', {}).get(
                'options', {}
            ).get('postdelete_retries', 10)
            postdelete_retry_delay = resource_queries.get('statecheck', {}).get(
                'options', {}
            ).get('postdelete_retry_delay', 5)

        return TeardownQueries(
            exists=exists,
            delete=delete,
            postdelete_exists_retries=postdelete_retries,
            postdelete_exists_retry_delay=postdelete_retry_delay
        )

    def _add_reverse_export_mappings(
        self,
        resource: Dict,
        full_context: Dict
    ):
        """Add reverse export map variables to full context."""
        if 'exports' not in resource:
            return

        for export in resource['exports']:
            if isinstance(export, dict):
                for key, lookup_key in export.items():
                    # Get the value from full_context using the lookup_key
                    if lookup_key in full_context:
                        # Add new mapping using the export key and looked up value
                        full_context[key] = full_context[lookup_key]

    def _perform_pre_delete_check(
        self,
        resource: Dict,
        full_context: Dict,
        queries: TeardownQueries,
        resource_type: str,
        dry_run: bool,
        show_queries: bool
    ) -> Tuple[bool, bool]:
        """Perform pre-delete existence check. Returns (resource_exists, ignore_errors)."""
        if resource_type == ResourceType.MULTI.value:
            self.logger.info("pre-delete check not supported for multi resources, skipping...")
            return True, True  # assume exists, ignore errors

        # For regular resources, check if exists
        resource_exists = self.check_if_resource_exists(
            True,  # assume exists
            resource,
            full_context,
            queries.exists.query,
            queries.exists.retries,
            queries.exists.retry_delay,
            dry_run,
            show_queries
        )

        return resource_exists, False

    def _delete_resource_if_exists(
        self,
        resource: Dict,
        full_context: Dict,
        queries: TeardownQueries,
        resource_exists: bool,
        ignore_errors: bool,
        dry_run: bool,
        show_queries: bool
    ) -> bool:
        """Delete resource if it exists. Returns True if deletion was attempted."""
        if not resource_exists:
            self.logger.info(f"resource [{resource['name']}] does not exist, skipping delete")
            return False

        self.delete_resource(
            resource,
            full_context,
            queries.delete.query,
            queries.delete.retries,
            queries.delete.retry_delay,
            dry_run,
            show_queries,
            ignore_errors
        )
        return True

    def _verify_deletion(
        self,
        resource: Dict,
        full_context: Dict,
        queries: TeardownQueries,
        dry_run: bool,
        show_queries: bool
    ) -> bool:
        """Verify resource was deleted. Returns True if deleted successfully."""
        resource_deleted = self.check_if_resource_exists(
            False,
            resource,
            full_context,
            queries.exists.query,
            queries.postdelete_exists_retries,
            queries.postdelete_exists_retry_delay,
            dry_run,
            show_queries,
            delete_test=True,
        )

        if resource_deleted:
            self.logger.info(f"✅ successfully deleted {resource['name']}")
            return True
        else:
            if not dry_run:
                catch_error_and_exit(
                    f"❌ failed to delete {resource['name']}.",
                    self.logger
                )
            return False

    def _process_resource(
        self,
        resource: Dict,
        dry_run: bool,
        show_queries: bool
    ):
        """Process a single resource for teardown."""
        print_unicode_box(f"Processing resource: [{resource['name']}]", BorderColor.RED)

        resource_type = get_type(resource, self.logger)

        # Skip non-resource types
        if resource_type not in (ResourceType.RESOURCE.value, ResourceType.MULTI.value):
            self.logger.debug(f"skipping resource [{resource['name']}] (type: {resource_type})")
            return

        self.logger.info(f"de-provisioning resource [{resource['name']}], type: {resource_type}")

        # Get full context
        full_context = get_full_context(self.env, self.global_context, resource, self.logger)

        # Evaluate condition
        if not self._evaluate_resource_condition(resource, full_context):
            return

        # Add reverse export mappings
        self._add_reverse_export_mappings(resource, full_context)

        # Get resource queries
        resource_queries = get_queries(
            self.env,
            self.stack_dir,
            'resources',
            resource,
            full_context,
            self.logger
        )

        # Build teardown queries
        queries = self._build_teardown_queries(resource_queries)

        if not queries.delete.query:
            self.logger.info(f"delete query not defined for [{resource['name']}], skipping...")
            return

        # Pre-delete check
        resource_exists, ignore_errors = self._perform_pre_delete_check(
            resource, full_context, queries, resource_type, dry_run, show_queries
        )

        # Delete resource if it exists
        deletion_attempted = self._delete_resource_if_exists(
            resource, full_context, queries, resource_exists,
            ignore_errors, dry_run, show_queries
        )

        if not deletion_attempted:
            return

        # Verify deletion
        self._verify_deletion(resource, full_context, queries, dry_run, show_queries)

    def collect_exports(self, show_queries, dry_run):
        """Collect exports from all resources before teardown."""
        self.logger.info(
            f"collecting exports for [{self.stack_name}] in [{self.stack_env}] environment"
        )

        for resource in self.manifest.get('resources', []):
            self._collect_resource_exports(resource, show_queries, dry_run)

    def run(self, dry_run, show_queries, on_failure):
        """Run the teardown process for all resources."""
        start_time = datetime.datetime.now()

        self.logger.info(
            f"tearing down [{self.stack_name}] in [{self.stack_env}] "
            f"environment {'(dry run)' if dry_run else ''}"
        )

        # Collect all exports
        self.collect_exports(show_queries, dry_run)

        # Process resources in reverse order
        for resource in reversed(self.manifest['resources']):
            self._process_resource(resource, dry_run, show_queries)

        elapsed_time = datetime.datetime.now() - start_time
        self.logger.info(f"deployment completed in {elapsed_time}")
