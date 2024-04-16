import sys
from ..lib.utils import run_test
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

    def run(self, dry_run, on_failure):
        
        self.logger.info(f"Testing [{self.stack_name}] in [{self.stack_env}] environment {'(dry run)' if dry_run else ''}")

        # get global context and pull providers
        self.global_context, self.providers = get_global_context_and_providers(self.env, self.manifest, self.vars, self.stack_env, self.stackql, self.logger)

        for resource in self.manifest.get('resources', []):

            # get full context
            full_context = get_full_context(self.env, self.global_context, resource, self.logger)    

            # get resource queries
            test_queries, test_query_options = get_queries(self.env, self.stack_dir, 'stackql_tests', resource, full_context, False, self.logger)
                
            if 'postdeploy' in test_queries:
                postdeploy_query = test_queries['postdeploy']

            #
            # postdeploy check
            #
            post_deploy_check_passed = False
            if not postdeploy_query:
                post_deploy_check_passed = True
                self.logger.info(f"test not configured for [{resource['name']}], not waiting...")
            elif dry_run:
                post_deploy_check_passed = True
                self.logger.info(f"test query for [{resource['name']}]:\n\n{postdeploy_query}\n")
            else:
                post_deploy_check_passed = run_test(resource, postdeploy_query, self.stackql, self.logger)

            #
            # postdeploy check complete
            #
            if not post_deploy_check_passed:
                error_message = f"test failed for {resource['name']}."
                self.logger.error(error_message)
                sys.exit(error_message)

            if not dry_run:
                self.logger.info(f"test passed for {resource['name']}")
