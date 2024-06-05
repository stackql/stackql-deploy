import os, sys, subprocess, json
from ..lib.utils import run_test, perform_retries, run_stackql_command, catch_error_and_exit, run_stackql_query
from ..lib.config import setup_environment, load_manifest, get_global_context_and_providers, get_full_context
from ..lib.templating import get_queries

class StackQLProvisioner:
    
    def __init__(self, stackql, vars, logger, stack_dir, stack_env):
        self.stackql = stackql
        self.vars = vars
        self.logger = logger
        self.stack_dir = stack_dir
        self.stack_env = stack_env
        self.env = setup_environment(self.stack_dir, self.logger)
        self.manifest = load_manifest(self.stack_dir, self.logger)
        self.stack_name = self.manifest.get('name', stack_dir)
        
    def _run_ext_script(self, cmd, exports=None):
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, shell=True)
            self.logger.debug(f"script output: {result.stdout}")
            if not exports:
                return True                
        except Exception as e:
            catch_error_and_exit(f"script failed: {e}", self.logger)
            return None

        # we must be expecting exports
        try:
            exported_vars = json.loads(result.stdout)
            # json_output should be a dictionary
            if not isinstance(exported_vars, dict):
                catch_error_and_exit(f"external scripts must be convertible to a dictionary {exported_vars}", self.logger)
                return None
            # you should be able to find each name in exports in the output object
            for export in exports:
                if export not in exported_vars:
                    catch_error_and_exit(f"exported variable '{export}' not found in script output", self.logger)
                    return None
            return exported_vars
        except json.JSONDecodeError:
            catch_error_and_exit(f"external scripts must return a valid JSON object {result.stdout}", self.logger)
            return None


    def _export_vars(self, resource, export, expected_exports, protected_exports):
        for key in expected_exports:
            if key not in export:
                catch_error_and_exit(f"exported key '{key}' not found in exports for {resource['name']}.", self.logger)

        for key, value in export.items():
            if key in protected_exports:
                mask = '*' * len(str(value))
                self.logger.info(f"🔒  set protected variable [{key}] to [{mask}] in exports")
            else:
                self.logger.info(f"➡️  set [{key}] to [{value}] in exports")

            self.global_context[key] = value  # Update global context with exported values        


    def run(self, dry_run, on_failure):

        self.logger.info(f"Deploying [{self.stack_name}] in [{self.stack_env}] environment {'(dry run)' if dry_run else ''}")

        # get global context and pull providers
        self.global_context, self.providers = get_global_context_and_providers(self.env, self.manifest, self.vars, self.stack_env, self.stack_name, self.stackql, self.logger)            

        for resource in self.manifest.get('resources', []):

            self.logger.info(f"processing resource: {resource['name']}")

            type = resource.get('type', 'resource')

            if type not in ['resource', 'query', 'script']:
                catch_error_and_exit(f"resource type must be 'resource', 'script' or 'query', got '{type}'", self.logger)

            # get full context
            full_context = get_full_context(self.env, self.global_context, resource, self.logger)    

            if type == 'script':
                self.logger.info(f"running script for {resource['name']}...")
                script_tempate = resource.get('run', None)
                if not script_tempate:
                    catch_error_and_exit("script resource must include 'run' key", self.logger)

                script = self.env.from_string(script_tempate).render(full_context)

                if dry_run:
                    dry_run_script = script.replace('""', '"<evaluated>"')
                    self.logger.info(f"dry run script for [{resource['name']}]:\n\n{dry_run_script}\n")
                else:
                    # run the script from the systems shell
                    self.logger.info(f"running script for [{resource['name']}]...")
                    try:
                        ret_vars = self._run_ext_script(script, resource.get('exports', None))
                        if resource.get('exports', None):
                            self.logger.info(f"exported variables from script: {ret_vars}")
                            self._export_vars(resource, ret_vars, resource.get('exports', []), resource.get('protected', []))                            
                    except Exception as e:
                        catch_error_and_exit(f"script failed: {e}", self.logger)
                continue

            fail_on_missing_test_query = False

            if type == 'resource':
                # get resource queries
                resource_queries, resource_query_options = get_queries(self.env, self.stack_dir, 'stackql_resources', resource, full_context, True, self.logger)

                create_query = None
                createorupdate_query = None
                update_query = None

                if not (('create' in resource_queries or 'createorupdate' in resource_queries) or ('create' in resource_queries and 'update' in resource_queries)):
                    catch_error_and_exit("iql file must include either 'create' or 'createorupdate' anchor, or both 'create' and 'update' anchors.", self.logger)

                if 'create' in resource_queries:
                    create_query = resource_queries['create']

                if 'createorupdate' in resource_queries:
                    createorupdate_query = resource_queries['createorupdate']

                if 'update' in resource_queries:
                    update_query = resource_queries['update']

            if type == 'query':
                fail_on_missing_test_query = True

            # get test queries
            test_queries, test_query_options = get_queries(self.env, self.stack_dir, 'stackql_queries', resource, full_context, fail_on_missing_test_query, self.logger)

            preflight_query = None
            postdeploy_query = None
            exports_query = None

            if test_queries == {}:
                self.logger.info(f"test query file not found for {resource['name']}. Skipping tests.")
            else:
                if 'preflight' in test_queries:
                    preflight_query = test_queries['preflight']
                
                if 'postdeploy' in test_queries:
                    postdeploy_query = test_queries['postdeploy']
                    postdeploy_retries = test_query_options.get('postdeploy', {}).get('retries', 10)
                    postdeploy_retry_delay = test_query_options.get('postdeploy', {}).get('retry_delay', 10)  

                if 'exports' in test_queries:
                    # export variables from resource
                    exports_query = test_queries['exports']
                    exports_retries = test_query_options.get('exports', {}).get('retries', 10)
                    exports_retry_delay = test_query_options.get('exports', {}).get('retry_delay', 10)

            if type == 'query':
                if not exports_query:
                    catch_error_and_exit("iql file must include 'exports' anchor for query type resources.", self.logger)

            if type == 'resource':

                #
                # run pre flight check (check if resource exists)
                #
                resource_exists = False
                is_correct_state = False

                if not preflight_query:
                    self.logger.info(f"pre-flight check not configured for [{resource['name']}]")
                elif dry_run:
                    self.logger.info(f"dry run pre-flight check for [{resource['name']}]:\n\n{preflight_query}\n")
                else:
                    self.logger.info(f"running pre-flight check for [{resource['name']}]...")
                    resource_exists = run_test(resource, preflight_query, self.stackql, self.logger)

                #
                # deploy
                #
                if createorupdate_query:
                    # disregard preflight check result if createorupdate is present
                    if dry_run:
                        self.logger.info(f"dry run create_or_update for [{resource['name']}]:\n\n{createorupdate_query}\n")
                    else:
                        self.logger.info(f"creating/updating [{resource['name']}]...")
                        msg = run_stackql_command(createorupdate_query, self.stackql, self.logger)
                        self.logger.debug(f"create or update response: {msg}")
                else:
                    if not resource_exists:
                        if dry_run:
                            self.logger.info(f"dry run create for [{resource['name']}]:\n\n{create_query}\n")
                        else:
                            self.logger.info(f"[{resource['name']}] does not exist, creating...")
                            msg = run_stackql_command(create_query, self.stackql, self.logger)
                            self.logger.debug(f"create response: {msg}")
                    else:
                        # resource exists, check state using postdeploy query as a preflight state check
                        if not postdeploy_query:
                            self.logger.info(f"state check not configured for [{resource['name']}], state check bypassed...")
                            is_correct_state = True
                        elif dry_run:
                            self.logger.info(f"dry run state check for [{resource['name']}]:\n\n{postdeploy_query}\n")
                        else:
                            self.logger.info(f"running state check for [{resource['name']}]...")
                            is_correct_state = perform_retries(resource, postdeploy_query, postdeploy_retries, postdeploy_retry_delay, self.stackql, self.logger)
                            self.logger.info(f"state check result for [{resource['name']}] : {is_correct_state}")

                        if update_query:
                            if dry_run:
                                self.logger.info(f"dry run update for [{resource['name']}]:\n\n{update_query}\n")
                            if not is_correct_state:
                                self.logger.info(f"[{resource['name']}] exists and is not in the desired state, updating...")
                                msg = run_stackql_command(update_query, self.stackql, self.logger)
                                self.logger.debug(f"update response: {msg}")
                            else:
                                self.logger.info(f"[{resource['name']}] is in the desired state 👍")
                        else:
                            self.logger.info(f"[{resource['name']}] exists, no update query defined however, skipping update...")                            

                #
                # postdeploy check
                #
                if not postdeploy_query:
                    self.logger.info(f"post-deploy check not configured for [{resource['name']}], not waiting...")
                else:
                    if dry_run:
                        self.logger.info(f"dry run post-deploy check for [{resource['name']}]:\n\n{postdeploy_query}\n")
                    else:
                        if not is_correct_state:
                            self.logger.info(f"running post deploy check for [{resource['name']}], waiting...")
                            is_correct_state = perform_retries(resource, postdeploy_query, postdeploy_retries, postdeploy_retry_delay, self.stackql, self.logger)
                    
                #
                # postdeploy check complete
                #
                if postdeploy_query and not is_correct_state:
                    catch_error_and_exit(f"❌ deployment failed for {resource['name']} after post-deploy checks.", self.logger)

            #
            # exports
            #
            if exports_query:
                expected_exports = resource.get('exports', [])

                if len(expected_exports) > 0:
                    protected_exports = resource.get('protected', [])

                    if not dry_run:
                        self.logger.info(f"exporting variables for [{resource['name']}]...")
                        exports = run_stackql_query(exports_query, self.stackql, True, self.logger, exports_retries, exports_retry_delay)
                        self.logger.debug(f"exports: {exports}")
                        
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

                        self._export_vars(resource, export_data, expected_exports, protected_exports)
                    else:
                        self.logger.info(f"dry run exports query for [{resource['name']}]:\n\n{exports_query}\n")

            if not dry_run:
                if type == 'resource':
                    self.logger.info(f"✅ successfully deployed {resource['name']}")
                elif type == 'query':
                    self.logger.info(f"✅ successfully exported variables for query in {resource['name']}")
