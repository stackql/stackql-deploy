import os, sys
from ..lib.utils import pull_providers, run_test, perform_retries
from ..lib.config import load_manifest, render_globals, render_properties
from ..lib.templating import render_queries, load_sql_queries
from jinja2 import Environment, FileSystemLoader, select_autoescape

class StackQLProvisioner:

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
            self.logger.debug(f"full context: {full_context}")
            
            #
            # render templates
            #
            resource_template_path = os.path.join(self.stack_dir, 'stackql_resources', f"{resource['name']}.iql")
            resource_query_templates, resource_query_options = load_sql_queries(resource_template_path)
            resource_queries = render_queries(self.env, resource_query_templates, full_context)
            self.logger.debug(f"resource queries: {resource_queries}")

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

            test_template_path = os.path.join(self.stack_dir, 'stackql_tests', f"{resource['name']}.iql")

            preflight_query = None
            postdeploy_query = None

            if not os.path.exists(test_template_path):
                self.logger.info(f"test query file not found for {resource['name']}. Skipping tests.")
            else:
                test_query_templates, test_query_options = load_sql_queries(test_template_path)
                test_queries = render_queries(self.env, test_query_templates, full_context)
                self.logger.debug(f"test queries: {test_queries}")

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
                    self.stackql.executeStmt(create_query)
            else:
                if not resource_exists:
                    if dry_run:
                        self.logger.info(f"dry run create for [{resource['name']}]:\n\n{create_query}\n")
                    else:
                        self.logger.info(f"creating [{resource['name']}]...")
                        self.stackql.execute(create_query)
                else:
                    if dry_run:
                        self.logger.info(f"dry run update for [{resource['name']}]:\n\n{update_query}\n")
                    else:
                        self.logger.info(f"updating [{resource['name']}].")
                        self.stackql.execute(update_query)

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
