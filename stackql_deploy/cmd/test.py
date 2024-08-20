import sys
from ..lib.utils import run_test, perform_retries, catch_error_and_exit, run_stackql_query, export_vars, show_query, get_type
from ..lib.config import setup_environment, load_manifest, get_global_context_and_providers, get_full_context
from ..lib.templating import get_queries

class StackQLTestRunner:

    def __init__(self, stackql, vars, logger, stack_dir, stack_env):
        self.stackql = stackql
        self.vars = vars
        self.logger = logger
        self.stack_dir = stack_dir
        self.stack_env = stack_env
        self.env = setup_environment(self.stack_dir, self.logger)
        self.manifest = load_manifest(self.stack_dir, self.logger)
        self.stack_name = self.manifest.get('name', stack_dir)

    def run(self, dry_run, show_queries, on_failure):
        
        self.logger.info(f"testing [{self.stack_name}] in [{self.stack_env}] environment {'(dry run)' if dry_run else ''}")

        # get global context and pull providers
        self.global_context, self.providers = get_global_context_and_providers(self.env, self.manifest, self.vars, self.stack_env, self.stack_name, self.stackql, self.logger)

        for resource in self.manifest.get('resources', []):

            self.logger.info(f"testing resource [{resource['name']}]")

            type = get_type(resource, self.logger)

            # get full context
            full_context = get_full_context(self.env, self.global_context, resource, self.logger)    

            #
            # get test queries
            #
            test_queries, test_query_options = get_queries(self.env, self.stack_dir, 'resources', resource, full_context, False, self.logger)

            postdeploy_query = None
            exports_query = None

            if 'postdeploy' in test_queries:
                postdeploy_query = test_queries['postdeploy']
                postdeploy_retries = test_query_options.get('postdeploy', {}).get('retries', 1)
                postdeploy_retry_delay = test_query_options.get('postdeploy', {}).get('retry_delay', 0)                

            if 'exports' in test_queries:
                # export variables from resource
                exports_query = test_queries['exports']
                exports_retries = test_query_options.get('exports', {}).get('retries', 1)
                exports_retry_delay = test_query_options.get('exports', {}).get('retry_delay', 0)  
            else:
                if type == 'query':
                    catch_error_and_exit("iql file must include 'exports' anchor for query type resources.", self.logger)                              

            #
            # postdeploy check
            #
            is_correct_state = False
            if not postdeploy_query:
                is_correct_state = True
                if resource.get('type') and resource['type'] == 'query':
                    self.logger.debug(f"❓ test not configured for [{resource['name']}]")
                else:
                    self.logger.info(f"❓ test not configured for [{resource['name']}]")
            elif dry_run:
                is_correct_state = True
                self.logger.info(f"test query for [{resource['name']}]:\n\n{postdeploy_query}\n")
            else:
                self.logger.info(f"🔎 checking state for [{resource['name']}]...")
                show_query(show_queries, postdeploy_query, self.logger)
                is_correct_state = perform_retries(resource, postdeploy_query, postdeploy_retries, postdeploy_retry_delay, self.stackql, self.logger)

            #
            # postdeploy check complete
            #

            if not is_correct_state:
                catch_error_and_exit(f"❌ test failed for {resource['name']}.", self.logger)

            #
            # exports
            #
            if exports_query:
                expected_exports = resource.get('exports', [])

                if len(expected_exports) > 0:
                    protected_exports = resource.get('protected', [])

                    if not dry_run:
                        self.logger.info(f"📦 exporting variables for [{resource['name']}]...")
                        show_query(show_queries, exports_query, self.logger)
                        exports = run_stackql_query(exports_query, self.stackql, True, self.logger, exports_retries, exports_retry_delay)
                        self.logger.debug(f"exports: {exports}")
                        
                        if exports is None:
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
                                # Check if the key's value is a simple string or needs special handling
                                if isinstance(export.get(key), dict) and 'String' in export[key]:
                                    # Assume complex object that needs extraction from 'String'
                                    export_data[key] = export[key]['String']
                                else:
                                    # Treat as a simple key-value pair
                                    export_data[key] = export.get(key, '')  # Default to empty string if key is missing

                        export_vars(self, resource, export_data, expected_exports, protected_exports)
                    else:
                        export_data = {key: "<evaluated>" for key in expected_exports}
                        export_vars(self, resource, export_data, expected_exports, protected_exports)
                        self.logger.info(f"dry run exports query for [{resource['name']}]:\n\n{exports_query}\n")

            if not dry_run:
                self.logger.info(f"✅ test passed for {resource['name']}")
