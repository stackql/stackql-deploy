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
