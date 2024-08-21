import sys
from ..lib.utils import perform_retries, run_stackql_command, catch_error_and_exit, run_stackql_query, export_vars, show_query, get_type
from ..lib.config import setup_environment, load_manifest, get_global_context_and_providers, get_full_context
from ..lib.templating import get_queries

class StackQLDeProvisioner:

    def __init__(self, stackql, vars, logger, stack_dir, stack_env):
        self.stackql = stackql
        self.vars = vars
        self.logger = logger
        self.stack_dir = stack_dir
        self.stack_env = stack_env
        self.env = setup_environment(self.stack_dir, self.logger)
        self.manifest = load_manifest(self.stack_dir, self.logger)
        self.stack_name = self.manifest.get('name', stack_dir)

    def collect_exports(self, show_queries, dry_run):
        self.logger.info(f"collecting exports for [{self.stack_name}] in [{self.stack_env}] environment")

        for resource in self.manifest.get('resources', []):
            
            self.logger.info(f"getting exports for resource [{resource['name']}]")

            # get full context
            full_context = get_full_context(self.env, self.global_context, resource, self.logger)

            # get resource queries
            test_queries, test_query_options = get_queries(self.env, self.stack_dir, 'resources', resource, full_context, False, self.logger)

            exports_query = None

            if 'exports' in test_queries:
                exports_query = test_queries['exports']
                exports_retries = test_query_options.get('exports', {}).get('retries', 1)
                exports_retry_delay = test_query_options.get('exports', {}).get('retry_delay', 0)

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

                        if len(exports) == 0:
                            export_data = {key: '' for key in expected_exports}
                        
                        if len(exports) == 1 and isinstance(exports[0], dict):
                            # exports is a list with one dictionary
                            export = exports[0]
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

    def run(self, dry_run, show_queries, on_failure):

        self.logger.info(f"tearing down [{self.stack_name}] in [{self.stack_env}] environment {'(dry run)' if dry_run else ''}")

        # get global context and pull providers
        self.global_context, self.providers = get_global_context_and_providers(self.env, self.manifest, self.vars, self.stack_env, self.stack_name, self.stackql, self.logger)

        # Collect all exports
        self.collect_exports(show_queries, dry_run)

        for resource in reversed(self.manifest['resources']):
            # process resources in reverse order
            type = get_type(resource, self.logger)

            if type != 'resource':
                self.logger.debug(f"skipping resource [{resource['name']}] (type: {type})")
                continue
            else:
                self.logger.info(f"de-provisioning resource [{resource['name']}]")

            # get full context
            full_context = get_full_context(self.env, self.global_context, resource, self.logger)    

            # get resource queries
            resource_queries, resource_query_options = get_queries(self.env, self.stack_dir, 'resources', resource, full_context, True, self.logger)

            delete_query = None
            test_query = None

            if 'delete' in resource_queries:
                delete_query = resource_queries['delete']
            else:
                self.logger.info(f"delete query not defined for [{resource['name']}]")
                continue

            if 'preflight' in resource_queries:
                test_query = resource_queries['preflight']
                test_retries = resource_query_options.get('preflight', {}).get('retries', 1)
                test_retry_delay = resource_query_options.get('preflight', {}).get('retry_delay', 0)                
            elif 'postdeploy' in resource_queries:
                test_query = resource_queries['postdeploy']
                test_retries = resource_query_options.get('postdeploy', {}).get('retries', 1)
                test_retry_delay = resource_query_options.get('postdeploy', {}).get('retry_delay', 0)            
            else:
                self.logger.info(f"test queries not defined for [{resource['name']}]")
                continue                

            #
            # pre-delete check
            #
            if dry_run:
                self.logger.info(f"🔎 dry run pre-delete check for [{resource['name']}]:\n\n{test_query}\n")
            else:
                self.logger.info(f"🔎 checking if [{resource['name']}] exists...")
                show_query(show_queries, test_query, self.logger)
                resource_exists = perform_retries(resource, test_query, 1, 0, self.stackql, self.logger)
                if not resource_exists:
                    self.logger.info(f"resource [{resource['name']}] does not exist, skipping delete")
                    continue

            #
            # delete
            #
            if dry_run:
                self.logger.info(f"🚧 dry run delete for [{resource['name']}]:\n\n{delete_query}\n")
            else:
                self.logger.info(f"🚧 deleting [{resource['name']}]...")
                show_query(show_queries, delete_query, self.logger)
                msg = run_stackql_command(delete_query, self.stackql, self.logger)
                self.logger.debug(f"delete response: {msg}")

            #
            # confirm deletion
            #
            resource_deleted = False
            if dry_run:
                self.logger.info(f"🔎 dry run post-delete check for [{resource['name']}]:\n\n{test_query}\n")
            else:
                self.logger.info(f"🔎 checking if [{resource['name']}] exists...")
                show_query(show_queries, test_query, self.logger)
                resource_deleted = perform_retries(resource, test_query, 10, 10, self.stackql, self.logger, delete_test=True)
                if resource_deleted:
                    self.logger.info(f"✅ successfully deleted {resource['name']}")
                else:
                    catch_error_and_exit(f"❌ failed to delete {resource['name']}.", self.logger)
