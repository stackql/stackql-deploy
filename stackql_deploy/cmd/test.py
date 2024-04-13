import os
from ..lib.utils import pull_providers, run_test
from ..lib.config import load_manifest, render_globals, render_properties
from ..lib.templating import render_queries, load_sql_queries
from jinja2 import Environment, FileSystemLoader, select_autoescape

class StackQLTestRunner:

    def __init__(self, stackql, vars, logger, stack_dir, environment):
        self.stackql = stackql
        self.vars = vars
        self.logger = logger
        self.stack_dir = stack_dir
        self.environment = environment

        self.manifest = load_manifest(self.stack_dir)
        self.env = Environment(
            loader=FileSystemLoader(os.getcwd()),
            autoescape=select_autoescape()
        )
        self.global_vars = self.manifest.get('globals', [])
        self.providers = self.manifest.get('providers', [])
        pull_providers(self.providers, self.stackql, self.logger)

    def run(self, dry_run, on_failure):
        global_context = render_globals(self.environment, self.global_vars, self.env, self.vars)

        for resource in self.manifest['resources']:
            #
            # get props
            #
            prop_context = render_properties(self.env, self.vars, self.environment, resource['props'], global_context, self.logger)
            full_context = {**self.vars, **global_context, **prop_context}  # Combine all contexts
            
            #
            # render templates
            #
            test_template_path = os.path.join(self.stack_dir, 'stackql_tests', f"{resource['name']}.iql")

            postdeploy_query = None

            if not os.path.exists(test_template_path):
                self.logger.info(f"test query file not found for {resource['name']}. Skipping tests.")
            else:
                test_query_templates, test_query_options = load_sql_queries(test_template_path)
                test_queries = render_queries(self.env, test_query_templates, full_context)
                
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
                raise Exception(error_message)

            if not dry_run:
                self.logger.info(f"test passed for {resource['name']}")
