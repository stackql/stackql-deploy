# cmd/base.py
import os
import json
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple

from ..lib.utils import (
    perform_retries,
    run_stackql_command,
    catch_error_and_exit,
    run_stackql_query,
    export_vars,
    show_query,
    check_all_dicts,
    check_exports_as_statecheck_proxy,
)
from ..lib.config import load_manifest, get_global_context_and_providers
from ..lib.filters import setup_environment


@dataclass
class AuthConfig:
    """Custom authentication configuration with environment variables."""
    custom_auth: Optional[Dict]
    env_vars: Optional[Dict]


class StackQLBase:
    def __init__(self, stackql, vars, logger, stack_dir, stack_env):
        self.stackql = stackql
        self.vars = vars
        self.logger = logger
        self.stack_dir = stack_dir
        self.stack_env = stack_env
        self.env = setup_environment(self.stack_dir, self.logger)
        self.manifest = load_manifest(self.stack_dir, self.logger)
        self.stack_name = self.manifest.get('name', stack_dir)
        self.global_context, self.providers = get_global_context_and_providers(
            self.env,
            self.manifest,
            self.vars,
            self.stack_env,
            self.stack_name,
            self.stackql,
            self.logger
        )

    def process_custom_auth(self, resource: Dict, full_context: Dict) -> AuthConfig:
        """Process custom authentication configuration for a resource."""
        custom_auth = resource.get('auth', {})
        if not custom_auth:
            return AuthConfig(None, None)

        self.logger.info(f"🔑 custom auth is configured for [{resource['name']}]")

        env_vars = self._extract_auth_env_vars(custom_auth, full_context)
        return AuthConfig(custom_auth, env_vars if env_vars else None)

    def _extract_auth_env_vars(self, auth_config: Dict, full_context: Dict) -> Dict:
        """Recursively extract environment variables from auth configuration."""
        env_vars = {}
        auth_keys = {"username_var", "password_var", "credentialsenvvar", "keyIDenvvar"}

        def extract_recursive(config):
            for key, value in config.items():
                if key in auth_keys and value in full_context:
                    env_vars[value] = full_context[value]
                elif isinstance(value, dict):
                    extract_recursive(value)

        extract_recursive(auth_config)
        return env_vars

    def _build_export_data(
        self,
        exports_result: list,
        expected_exports: list,
        all_dicts: bool
    ) -> Dict:
        """Build export data dictionary from query results."""
        if not exports_result:
            return {}

        export = exports_result[0] if isinstance(exports_result[0], dict) else {}
        export_data = {}

        for item in expected_exports:
            if all_dicts:
                for key, val in item.items():
                    export_data[val] = self._extract_export_value(export, key)
            else:
                export_data[item] = self._extract_export_value(export, item)

        return export_data

    def _extract_export_value(self, export: Dict, key: str) -> Any:
        """Extract value from export, handling String wrapper objects."""
        value = export.get(key, '')
        if isinstance(value, dict) and 'String' in value:
            return value['String']
        return value

    def _validate_exports_result(self, exports_result: list, resource_name: str):
        """Validate exports query result format."""
        if not exports_result or len(exports_result) == 0:
            return

        # Check for errors
        if len(exports_result) >= 1 and isinstance(exports_result[0], dict):
            if '_stackql_deploy_error' in exports_result[0]:
                catch_error_and_exit(
                    f"exports query failed for {resource_name}\n\n"
                    f"Error details:\n{exports_result[0]['_stackql_deploy_error']}",
                    self.logger
                )
            elif 'error' in exports_result[0]:
                catch_error_and_exit(
                    f"exports query failed for {resource_name}\n\n"
                    f"Error details:\n{exports_result[0]['error']}",
                    self.logger
                )

        # Validate row count
        if len(exports_result) > 1:
            catch_error_and_exit(
                f"exports should include one row only, received {len(exports_result)} rows",
                self.logger
            )

        # Validate data type
        if len(exports_result) == 1 and not isinstance(exports_result[0], dict):
            catch_error_and_exit(
                f"exports must be a dictionary, received {str(exports_result[0])}",
                self.logger
            )

    def process_exports(
        self,
        resource,
        full_context,
        exports_query,
        exports_retries,
        exports_retry_delay,
        dry_run,
        show_queries,
        ignore_missing_exports=False
    ):
        """Process exports for a resource."""
        expected_exports = resource.get('exports', [])
        if len(expected_exports) == 0:
            return

        all_dicts = check_all_dicts(expected_exports, self.logger)
        protected_exports = resource.get('protected', [])

        if dry_run:
            self._handle_dry_run_exports(
                resource, exports_query, expected_exports, all_dicts, protected_exports
            )
        else:
            self._handle_live_exports(
                resource, full_context, exports_query, exports_retries,
                exports_retry_delay, show_queries, expected_exports,
                all_dicts, protected_exports, ignore_missing_exports
            )

    def _handle_dry_run_exports(
        self,
        resource,
        exports_query,
        expected_exports,
        all_dicts,
        protected_exports
    ):
        """Handle dry run export processing."""
        export_data = {}
        for item in expected_exports:
            if all_dicts:
                for _, val in item.items():
                    export_data[val] = "<evaluated>"
            else:
                export_data[item] = "<evaluated>"

        export_vars(self, resource, export_data, expected_exports, all_dicts, protected_exports)
        self.logger.info(
            f"📦 dry run exports query for [{resource['name']}]:\n\n/* exports query */\n{exports_query}\n"
        )

    def _handle_live_exports(
        self,
        resource,
        full_context,
        exports_query,
        exports_retries,
        exports_retry_delay,
        show_queries,
        expected_exports,
        all_dicts,
        protected_exports,
        ignore_missing_exports
    ):
        """Handle live export processing."""
        self.logger.info(f"📦 exporting variables for [{resource['name']}]...")
        show_query(show_queries, exports_query, self.logger)

        auth_config = self.process_custom_auth(resource, full_context)
        exports_result = run_stackql_query(
            exports_query,
            self.stackql,
            True,
            self.logger,
            custom_auth=auth_config.custom_auth,
            env_vars=auth_config.env_vars,
            retries=exports_retries,
            delay=exports_retry_delay
        )

        if not exports_result or len(exports_result) == 0:
            if ignore_missing_exports:
                return
            show_query(True, exports_query, self.logger)
            catch_error_and_exit(
                f"exports query failed for {resource['name']}",
                self.logger
            )

        self._validate_exports_result(exports_result, resource['name'])
        export_data = self._build_export_data(exports_result, expected_exports, all_dicts)
        export_vars(self, resource, export_data, expected_exports, all_dicts, protected_exports)

    def process_exports_from_result(self, resource, exports_result, expected_exports):
        """Process exports from cached query results."""
        if not exports_result or len(exports_result) == 0:
            return

        all_dicts = check_all_dicts(expected_exports, self.logger)
        protected_exports = resource.get('protected', [])

        self._validate_exports_result(exports_result, resource['name'])
        export_data = self._build_export_data(exports_result, expected_exports, all_dicts)
        export_vars(self, resource, export_data, expected_exports, all_dicts, protected_exports)

    def check_if_resource_exists(
        self,
        resource_exists,
        resource,
        full_context,
        exists_query,
        exists_retries,
        exists_retry_delay,
        dry_run,
        show_queries,
        delete_test=False
    ):
        """Check if a resource exists."""
        if not exists_query:
            check_type = 'post-delete' if delete_test else 'exists'
            self.logger.info(f"{check_type} check not configured for [{resource['name']}]")
            return False if delete_test else resource_exists

        return self._run_existence_check(
            resource, full_context, exists_query, exists_retries,
            exists_retry_delay, dry_run, show_queries, delete_test
        )

    def _run_existence_check(
        self,
        resource,
        full_context,
        query,
        retries,
        retry_delay,
        dry_run,
        show_queries,
        delete_test
    ):
        """Run existence check query."""
        check_type = 'post-delete' if delete_test else 'exists'

        if dry_run:
            self.logger.info(
                f"🔎 dry run {check_type} check for [{resource['name']}]:\n\n/* {check_type} query */\n{query}\n"
            )
            return True

        self.logger.info(f"🔎 running {check_type} check for [{resource['name']}]...")
        show_query(show_queries, query, self.logger)

        auth_config = self.process_custom_auth(resource, full_context)
        return perform_retries(
            resource, query, retries, retry_delay, self.stackql, self.logger,
            delete_test, custom_auth=auth_config.custom_auth, env_vars=auth_config.env_vars
        )

    def check_if_resource_is_correct_state(
        self,
        is_correct_state,
        resource,
        full_context,
        statecheck_query,
        statecheck_retries,
        statecheck_retry_delay,
        dry_run,
        show_queries
    ):
        """Check if resource is in correct state."""
        if not statecheck_query:
            self.logger.info(f"state check not configured for [{resource['name']}]")
            return True

        if dry_run:
            self.logger.info(
                f"🔎 dry run state check for [{resource['name']}]:\n\n/* state check query */\n{statecheck_query}\n"
            )
            return True

        self.logger.info(f"🔎 running state check for [{resource['name']}]...")
        show_query(show_queries, statecheck_query, self.logger)

        auth_config = self.process_custom_auth(resource, full_context)
        is_correct_state = perform_retries(
            resource, statecheck_query, statecheck_retries,
            statecheck_retry_delay, self.stackql, self.logger,
            False, custom_auth=auth_config.custom_auth, env_vars=auth_config.env_vars
        )

        state_icon = "👍" if is_correct_state else "👎"
        state_msg = "is in" if is_correct_state else "is not in"
        self.logger.info(f"{state_icon} [{resource['name']}] {state_msg} the desired state")

        return is_correct_state

    def check_state_using_exports_proxy(
        self,
        resource,
        full_context,
        exports_query,
        exports_retries,
        exports_retry_delay,
        dry_run,
        show_queries
    ):
        """Use exports query as a proxy for statecheck."""
        if dry_run:
            self.logger.info(
                f"🔎 dry run state check using exports proxy for [{resource['name']}]:\n\n"
                f"/* exports as statecheck proxy */\n{exports_query}\n"
            )
            return True, None

        self.logger.info(f"🔎 running state check using exports proxy for [{resource['name']}]...")
        show_query(show_queries, exports_query, self.logger)

        auth_config = self.process_custom_auth(resource, full_context)
        exports_result = run_stackql_query(
            exports_query,
            self.stackql,
            True,
            self.logger,
            custom_auth=auth_config.custom_auth,
            env_vars=auth_config.env_vars,
            retries=exports_retries,
            delay=exports_retry_delay
        )

        is_correct_state = check_exports_as_statecheck_proxy(exports_result, self.logger)

        state_icon = "👍" if is_correct_state else "👎"
        state_msg = "is in" if is_correct_state else "is not in"
        self.logger.info(
            f"{state_icon} [{resource['name']}] exports proxy indicates resource {state_msg} the desired state"
        )

        return is_correct_state, exports_result

    def _execute_resource_operation(
        self,
        operation_name: str,
        resource,
        full_context,
        query,
        retries,
        retry_delay,
        dry_run,
        show_queries,
        ignore_errors=False
    ) -> bool:
        """Execute a resource operation (create, update, or delete)."""
        operation_icons = {
            'create': '🚧',
            'update': '🔧',
            'delete': '🚧'
        }
        operation_messages = {
            'create': 'does not exist, creating',
            'update': 'updating',
            'delete': 'deleting'
        }

        icon = operation_icons.get(operation_name, '🚧')

        if dry_run:
            self.logger.info(
                f"{icon} dry run {operation_name} for [{resource['name']}]:\n\n/* {operation_name} query */\n{query}\n"
            )
            return False

        msg = operation_messages.get(operation_name, operation_name)
        self.logger.info(f"{icon} {msg} [{resource['name']}]...")
        show_query(show_queries, query, self.logger)

        auth_config = self.process_custom_auth(resource, full_context)
        result = run_stackql_command(
            query,
            self.stackql,
            self.logger,
            custom_auth=auth_config.custom_auth,
            env_vars=auth_config.env_vars,
            ignore_errors=ignore_errors,
            retries=retries,
            retry_delay=retry_delay
        )
        return True

    def create_resource(
        self,
        is_created_or_updated,
        resource,
        full_context,
        create_query,
        create_retries,
        create_retry_delay,
        dry_run,
        show_queries,
        ignore_errors=False
    ):
        """Create a resource."""
        executed = self._execute_resource_operation(
            'create', resource, full_context, create_query,
            create_retries, create_retry_delay, dry_run,
            show_queries, ignore_errors
        )
        return executed or is_created_or_updated

    def update_resource(
        self,
        is_created_or_updated,
        resource,
        full_context,
        update_query,
        update_retries,
        update_retry_delay,
        dry_run,
        show_queries,
        ignore_errors=False
    ):
        """Update a resource."""
        if not update_query:
            self.logger.info(f"update query not configured for [{resource['name']}], skipping update...")
            return is_created_or_updated

        executed = self._execute_resource_operation(
            'update', resource, full_context, update_query,
            update_retries, update_retry_delay, dry_run,
            show_queries, ignore_errors
        )
        return executed or is_created_or_updated

    def delete_resource(
        self,
        resource,
        full_context,
        delete_query,
        delete_retries,
        delete_retry_delay,
        dry_run,
        show_queries,
        ignore_errors=False,
    ):
        """Delete a resource."""
        if not delete_query:
            self.logger.info(f"delete query not configured for [{resource['name']}], skipping delete...")
            return

        self._execute_resource_operation(
            'delete', resource, full_context, delete_query,
            delete_retries, delete_retry_delay, dry_run,
            show_queries, ignore_errors
        )

    def run_command(self, command_query, command_retries, command_retry_delay, dry_run, show_queries):
        """Run a command."""
        if not command_query:
            self.logger.info("command query not configured, skipping command...")
            return

        if dry_run:
            self.logger.info(f"🚧 dry run command:\n\n{command_query}\n")
        else:
            self.logger.info("🚧 running command...")
            show_query(show_queries, command_query, self.logger)
            run_stackql_command(
                command_query,
                self.stackql,
                self.logger,
                retries=command_retries,
                retry_delay=command_retry_delay
            )

    def process_stack_exports(self, dry_run, output_file=None, elapsed_time=None):
        """Process root-level exports from manifest and write to JSON file."""
        if not output_file:
            return

        self.logger.info("📦 processing stack exports...")

        manifest_exports = self.manifest.get('exports', [])

        if dry_run:
            total_vars = len(manifest_exports) + 3
            self.logger.info(
                f"📁 dry run: would export {total_vars} variables to {output_file} "
                f"(including automatic stack_name, stack_env, and elapsed_time)"
            )
            return

        export_data = self._build_stack_export_data(manifest_exports, elapsed_time)
        self._write_exports_file(output_file, export_data)

    def _build_stack_export_data(self, manifest_exports, elapsed_time):
        """Build stack export data dictionary."""
        export_data = {
            'stack_name': self.stack_name,
            'stack_env': self.stack_env
        }
        missing_vars = []

        for var_name in manifest_exports:
            if var_name in ('stack_name', 'stack_env'):
                continue

            if var_name in self.global_context:
                value = self.global_context[var_name]
                # Parse JSON strings back to their original type
                try:
                    if isinstance(value, str) and (value.startswith('[') or value.startswith('{')):
                        value = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    pass
                export_data[var_name] = value
            else:
                missing_vars.append(var_name)

        if missing_vars:
            catch_error_and_exit(
                f"exports failed: variables not found in context: {missing_vars}",
                self.logger
            )

        if elapsed_time is not None:
            export_data['elapsed_time'] = str(elapsed_time)

        return export_data

    def _write_exports_file(self, output_file, export_data):
        """Write exports data to JSON file."""
        dest_dir = os.path.dirname(output_file)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)

        try:
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            self.logger.info(f"✅ exported {len(export_data)} variables to {output_file}")
        except Exception as e:
            catch_error_and_exit(f"failed to write exports file {output_file}: {e}", self.logger)
