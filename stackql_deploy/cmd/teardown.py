import os
from ..lib.utils import pull_providers, perform_retries
from ..lib.config import load_manifest, render_globals, render_properties
from ..lib.templating import render_queries, load_sql_queries
from jinja2 import Environment, FileSystemLoader, select_autoescape

class StackQLDeProvisioner:

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


        for resource in reversed(self.manifest['resources']):
            # process resources in reverse order

            #
            # get props
            #
            prop_context = render_properties(self.env, self.vars, self.environment, resource['props'], global_context, self.logger)
            full_context = {**self.vars, **global_context, **prop_context}  # Combine all contexts
            
            #
            # render templates
            #
            resource_template_path = os.path.join(self.stack_dir, 'stackql_resources', f"{resource['name']}.iql")
            resource_query_templates, resource_query_options = load_sql_queries(resource_template_path)
            resource_queries = render_queries(self.env, resource_query_templates, full_context)

            delete_query = None

            if 'delete' in resource_queries:
                delete_query = resource_queries['delete']

            test_template_path = os.path.join(self.stack_dir, 'stackql_tests', f"{resource['name']}.iql")

            preflight_query = None

            if not os.path.exists(test_template_path):
                self.logger.info(f"test query file not found for {resource['name']}. Skipping tests.")
            else:
                test_query_templates, test_query_options = load_sql_queries(test_template_path)
                test_queries = render_queries(self.env, test_query_templates, full_context)

                if 'preflight' in test_queries:
                    preflight_query = test_queries['preflight']

            #
            # delete
            #
            if delete_query:
                if dry_run:
                    self.logger.info(f"dry run delete for [{resource['name']}]:\n\n{delete_query}\n")
                else:
                    self.logger.info(f"deleting [{resource['name']}]...")
                    self.stackql.executeStmt(delete_query)
            else:
                self.logger.info(f"delete query not defined for [{resource['name']}]")

            #
            # confirm deletion
            #
            resource_deleted = False
            if not preflight_query:
                self.logger.info(f"post delete (pre-flight) check not configured for [{resource['name']}]")
            elif dry_run:
                self.logger.info(f"dry run delete (pre-flight) check for [{resource['name']}]:\n\n{preflight_query}\n")
            else:
                resource_deleted = perform_retries(resource, preflight_query, 10, 10, self.stackql, self.logger, delete_test=True)

            if not dry_run and not resource_deleted:
                error_message = f"failed to delete {resource['name']}."
                self.logger.error(error_message)
                raise Exception(error_message)
            else:
                self.logger.info(f"successfully deleted {resource['name']}")
