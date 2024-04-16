import sys
from ..lib.utils import run_test, perform_retries, run_stackql_command
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
        
    def run(self, dry_run, on_failure):

        # get global context and pull providers
        self.global_context, self.providers = get_global_context_and_providers(self.env, self.manifest, self.vars, self.stack_env, self.stackql, self.logger)            

        for resource in self.manifest.get('resources', []):

            # get full context
            full_context = get_full_context(self.env, self.global_context, resource, self.logger)    

            # get resource queries
            resource_queries, resource_query_options = get_queries(self.env, self.stack_dir, 'stackql_resources', resource, full_context, True, self.logger)

            # get resource queries
            test_queries, test_query_options = get_queries(self.env, self.stack_dir, 'stackql_tests', resource, full_context, False, self.logger)

            create_query = None
            createorupdate_query = None
            update_query = None

            if not (('create' in resource_queries or 'createorupdate' in resource_queries) or ('create' in resource_queries and 'update' in resource_queries)):
                raise ValueError("iql file must include either 'create' or 'createorupdate' anchor, or both 'create' and 'update' anchors.")

            if 'create' in resource_queries:
                create_query = resource_queries['create']

            if 'createorupdate' in resource_queries:
                createorupdate_query = resource_queries['createorupdate']

            if 'update' in resource_queries:
                update_query = resource_queries['update']

            preflight_query = None
            postdeploy_query = None

            if test_queries == {}:
                self.logger.info(f"test query file not found for {resource['name']}. Skipping tests.")
                continue
            else:
                if 'preflight' in test_queries:
                    preflight_query = test_queries['preflight']
                
                if 'postdeploy' in test_queries:
                    postdeploy_query = test_queries['postdeploy']
                    postdeploy_retries = test_query_options.get('postdeploy', {}).get('retries', 10)
                    postdeploy_retry_delay = test_query_options.get('postdeploy', {}).get('retry_delay', 10)                    

            #
            # run pre flight check
            #
            resource_exists = False
            if not preflight_query:
                self.logger.info(f"pre-flight check not configured for [{resource['name']}]")
            elif dry_run:
                self.logger.info(f"dry run pre-flight check for [{resource['name']}]:\n\n{preflight_query}\n")
            else:
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
                    self.logger.info(f"create or update response: {msg}")
            else:
                if not resource_exists:
                    if dry_run:
                        self.logger.info(f"dry run create for [{resource['name']}]:\n\n{create_query}\n")
                    else:
                        self.logger.info(f"creating [{resource['name']}]...")
                        msg = run_stackql_command(create_query, self.stackql, self.logger)
                        self.logger.info(f"create response: {msg}")
                else:
                    if dry_run:
                        self.logger.info(f"dry run update for [{resource['name']}]:\n\n{update_query}\n")
                    else:
                        self.logger.info(f"updating [{resource['name']}].")
                        msg = run_stackql_command(update_query, self.stackql, self.logger)
                        self.logger.info(f"update response: {msg}")

            #
            # postdeploy check
            #
            post_deploy_check_passed = False
            if not postdeploy_query:
                post_deploy_check_passed = True
                self.logger.info(f"post-deploy check not configured for [{resource['name']}], not waiting...")
            elif dry_run:
                post_deploy_check_passed = True
                self.logger.info(f"dry run post-deploy check for [{resource['name']}]:\n\n{postdeploy_query}\n")
            else:
                post_deploy_check_passed = perform_retries(resource, postdeploy_query, postdeploy_retries, postdeploy_retry_delay, self.stackql, self.logger)
                
            #
            # postdeploy check complete
            #
            if not post_deploy_check_passed:
                error_message = f"deployment failed for {resource['name']} after post-deploy checks."
                self.logger.error(error_message)
                sys.exit(error_message)

            if not dry_run:
                self.logger.info(f"successfully deployed {resource['name']}")
