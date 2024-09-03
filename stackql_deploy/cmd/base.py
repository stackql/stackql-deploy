from ..lib.utils import perform_retries, run_stackql_command, catch_error_and_exit, run_stackql_query, export_vars, show_query, get_type
from ..lib.config import setup_environment, load_manifest, get_global_context_and_providers, get_full_context
from ..lib.templating import get_queries

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
        self.global_context, self.providers = get_global_context_and_providers(self.env, self.manifest, self.vars, self.stack_env, self.stack_name, self.stackql, self.logger)

    def process_exports(self, resource, exports_query, exports_retries, exports_retry_delay, dry_run, show_queries,ignore_missing_exports=False):
        expected_exports = resource.get('exports', [])

        if len(expected_exports) > 0:
            protected_exports = resource.get('protected', [])

            if dry_run:
                export_data = {key: "<evaluated>" for key in expected_exports}
                export_vars(self, resource, export_data, expected_exports, protected_exports)
                self.logger.info(f"📦 dry run exports query for [{resource['name']}]:\n\n/* exports query */\n{exports_query}\n")
            else:
                self.logger.info(f"📦 exporting variables for [{resource['name']}]...")
                show_query(show_queries, exports_query, self.logger)
                exports = run_stackql_query(exports_query, self.stackql, True, self.logger, exports_retries, exports_retry_delay)
                self.logger.debug(f"exports: {exports}")

                if (exports is None or len(exports) == 0):
                    if ignore_missing_exports:
                        return
                    else:
                        catch_error_and_exit(f"exports query failed for {resource['name']}", self.logger)
                
                if len(exports) > 1:
                    catch_error_and_exit(f"exports should include one row only, received {str(len(exports))} rows", self.logger)

                if len(exports) == 1 and not isinstance(exports[0], dict):
                    catch_error_and_exit(f"exports must be a dictionary, received {str(exports[0])}", self.logger)                            

                export = exports[0]
                if len(exports) == 0:
                    export = {key: '' for key in expected_exports}
                else:
                    export_data = {}
                    for key in expected_exports:
                        if isinstance(export.get(key), dict) and 'String' in export[key]:
                            export_data[key] = export[key]['String']
                        else:
                            export_data[key] = export.get(key, '')

                export_vars(self, resource, export_data, expected_exports, protected_exports)

    def check_if_resource_exists(self, resource_exists, resource, exists_query, exists_retries, exists_retry_delay, dry_run, show_queries, delete_test=False):
        check_type = 'exists'
        if delete_test:
            check_type = 'post-delete'
        if exists_query:
            if dry_run:
                self.logger.info(f"🔎 dry run {check_type} check for [{resource['name']}]:\n\n/* exists query */\n{exists_query}\n")
            else:
                self.logger.info(f"🔎 running {check_type} check for [{resource['name']}]...")
                show_query(show_queries, exists_query, self.logger)
                resource_exists = perform_retries(resource, exists_query, exists_retries, exists_retry_delay, self.stackql, self.logger, delete_test)
        else:
            self.logger.info(f"{check_type} check not configured for [{resource['name']}]")
            if delete_test:
                resource_exists = False
        return resource_exists

    def check_if_resource_is_correct_state(self, is_correct_state, resource, statecheck_query, statecheck_retries, statecheck_retry_delay, dry_run, show_queries):
        if statecheck_query:
            if dry_run:
                self.logger.info(f"🔎 dry run state check for [{resource['name']}]:\n\n/* state check query */\n{statecheck_query}\n")
            else:
                self.logger.info(f"🔎 running state check for [{resource['name']}]...")
                show_query(show_queries, statecheck_query, self.logger)
                is_correct_state = perform_retries(resource, statecheck_query, statecheck_retries, statecheck_retry_delay, self.stackql, self.logger)
                if is_correct_state:
                    self.logger.info(f"👍 [{resource['name']}] is in the desired state")
                else:
                    self.logger.info(f"👎 [{resource['name']}] is not in the desired state")
        else:
            self.logger.info(f"state check not configured for [{resource['name']}]")
            is_correct_state = True
        return is_correct_state
    
    def create_resource(self, is_created_or_updated, resource, create_query, create_retries, create_retry_delay, dry_run, show_queries, ignore_errors=False):
        if dry_run:
            self.logger.info(f"🚧 dry run create for [{resource['name']}]:\n\n/* insert (create) query */\n{create_query}\n")
        else:
            self.logger.info(f"[{resource['name']}] does not exist, creating 🚧...")
            show_query(show_queries, create_query, self.logger)
            msg = run_stackql_command(create_query, self.stackql, self.logger, ignore_errors=ignore_errors, retries=create_retries, retry_delay=create_retry_delay)
            self.logger.debug(f"create response: {msg}")
            is_created_or_updated = True
        return is_created_or_updated

    def update_resource(self, is_created_or_updated, resource, update_query, update_retries, update_retry_delay, dry_run, show_queries, ignore_errors=False):
        if update_query:
            if dry_run:
                self.logger.info(f"🚧 dry run update for [{resource['name']}]:\n\n/* update query */\n{update_query}\n")
            else:
                self.logger.info(f"🔧 updating [{resource['name']}]...")
                show_query(show_queries, update_query, self.logger)
                msg = run_stackql_command(update_query, self.stackql, self.logger, ignore_errors=ignore_errors, retries=update_retries, retry_delay=update_retry_delay)
                self.logger.debug(f"update response: {msg}")
                is_created_or_updated = True
        else:
            self.logger.info(f"update query not configured for [{resource['name']}], skipping update...")
        return is_created_or_updated
    
    def delete_resource(self, resource, delete_query, delete_retries, delete_retry_delay, dry_run, show_queries, ignore_errors=False):
        if delete_query:
            if dry_run:
                self.logger.info(f"🚧 dry run delete for [{resource['name']}]:\n\n{delete_query}\n")
            else:
                self.logger.info(f"🚧 deleting [{resource['name']}]...")
                show_query(show_queries, delete_query, self.logger)
                msg = run_stackql_command(delete_query, self.stackql, self.logger, ignore_errors=ignore_errors, retries=delete_retries, retry_delay=delete_retry_delay)
                self.logger.debug(f"delete response: {msg}")
        else:
            self.logger.info(f"delete query not configured for [{resource['name']}], skipping delete...")
