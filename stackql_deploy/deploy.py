import time, os, yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

class StackQLProvisioner:

    def __init__(self, stackql, vars, logger, stack_dir, environment):
        self.stackql = stackql
        self.vars = vars
        self.logger = logger
        self.stack_dir = stack_dir
        self.environment = environment
        self.manifest = self.load_manifest()
        self.env = Environment(
            loader=FileSystemLoader(os.getcwd()),
            autoescape=select_autoescape()
        )
        self.pull_providers()

    def pull_providers(self):
        installed_providers = self.stackql.execute("SHOW PROVIDERS")
        installed_names = {provider['name'] for provider in installed_providers}
        for provider in self.manifest.get('providers', []):
            if provider not in installed_names:
                self.logger.info(f"Pulling provider '{provider}'...")
                msg = self.stackql.execute(f"REGISTRY PULL {provider}")
                self.logger.info(msg)
            else:
                self.logger.info(f"Provider '{provider}' is already installed.")

    def load_manifest(self):
        # Load and parse the stackql_manifest.yml
        with open(os.path.join(self.stack_dir, 'stackql_manifest.yml')) as f:
            return yaml.safe_load(f)

    def _render_globals(self):
        # Render globals with vars
        global_context = {'environment': self.environment}  # Start with the environment as a global variable
        for global_var in self.manifest.get('globals', []):
            template = self.env.from_string(global_var['value'])
            global_context[global_var['name']] = template.render(vars=self.vars)
        return global_context

    def _render_properties(self, resource_props, global_context):
        # Render properties with globals and vars
        prop_context = {}
        for prop in resource_props:
            if 'value' in prop:
                # Single value for all environments
                template = self.env.from_string(prop['value'])
                prop_context[prop['name']] = template.render(globals=global_context, vars=self.vars)
            elif 'values' in prop:
                # Environment-specific values
                env_value = prop['values'].get(self.environment, {}).get('value')
                if env_value is not None:
                    template = self.env.from_string(env_value)
                    prop_context[prop['name']] = template.render(globals=global_context, vars=self.vars)
                else:
                    self.logger.error(f"No value specified for property '{prop['name']}' in environment '{self.environment}'.")
                    raise ValueError(f"No value specified for property '{prop['name']}' in environment '{self.environment}'.")
        return prop_context

    def run_test(self, resource, rendered_test_iql):
        try:
            test_result = self.stackql.execute(rendered_test_iql)
            self.logger.debug(f"test query result for [{resource['name']}]: {test_result}")
            
            if not test_result or 'count' not in test_result[0]:
                self.logger.error(f"test data structure unexpected for [{resource['name']}]: {test_result}")
                raise Exception(f"critical failure: test for {resource['name']} did not return expected 'count' field.")
            
            count = int(test_result[0]['count'])
            if count != 1:
                self.logger.debug(f"test result false for [{resource['name']}], expected 1 got {count}.")
                return False
            
            self.logger.debug(f"test result true for [{resource['name']}]")
            return True

        except Exception as e:
            self.logger.error(f"an exception occurred during testing for [{resource['name']}]: {str(e)}")
            raise Exception(f"testing for {resource['name']} failed due to an exception.") from e


    def load_sql_queries(self, file_path):
        """Loads SQL queries from a file, splits them by anchors, and extracts options."""
        queries = {}
        options = {}
        current_anchor = None
        query_buffer = []
        
        with open(file_path, 'r') as file:
            for line in file:
                if line.startswith('/*+') and '*/' in line:
                    # Store the current query under the last anchor
                    if current_anchor and query_buffer:
                        anchor_key, anchor_options = self.parse_anchor(current_anchor)
                        queries[anchor_key] = ''.join(query_buffer).strip()
                        options[anchor_key] = anchor_options
                        query_buffer = []
                    # Set the new anchor
                    current_anchor = line[line.find('/*+') + 3:line.find('*/')].strip()
                else:
                    query_buffer.append(line)
            
            # Store the last query if any
            if current_anchor and query_buffer:
                anchor_key, anchor_options = self.parse_anchor(current_anchor)
                queries[anchor_key] = ''.join(query_buffer).strip()
                options[anchor_key] = anchor_options

        return queries, options

    def parse_anchor(self, anchor):
        """Parse anchor to extract key and options."""
        parts = anchor.split(',')
        key = parts[0].strip()
        options = {}
        for part in parts[1:]:
            if '=' in part:
                option_key, option_value = part.split('=')
                options[option_key.strip()] = int(option_value.strip())
        return key, options

    def render_queries(self, queries, context):
        """Render queries with context using Jinja2."""
        rendered_queries = {}
        for key, query in queries.items():
            template = self.env.from_string(query)
            rendered_queries[key] = template.render(context)
        return rendered_queries

    def perform_retries(self, resource, query, retries, delay):
        attempt = 0
        while attempt < retries:
            result = self.run_test(resource, query)
            if result:
                return True
            attempt += 1
            time.sleep(delay)
        self.logger.error(f"failed after {retries} retries.")
        return False

    def run(self, dry_run, on_failure):
        global_context = self._render_globals()  # Step 1

        for resource in self.manifest['resources']:
            #
            # get props
            #
            prop_context = self._render_properties(resource['props'], global_context)  # Step 2 & 3
            full_context = {**self.vars, **global_context, **prop_context}  # Combine all contexts
            
            #
            # render templates
            #
            resource_template_path = os.path.join(self.stack_dir, 'stackql_resources', f"{resource['name']}.iql")
            resource_query_templates, resource_query_options = self.load_sql_queries(resource_template_path)
            resource_queries = self.render_queries(resource_query_templates, full_context)

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
                test_query_templates, test_query_options = self.load_sql_queries(test_template_path)
                test_queries = self.render_queries(test_query_templates, full_context)

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
                resource_exists = self.run_test(resource, preflight_query)

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
                post_deploy_check_passed = self.perform_retries(resource, postdeploy_query, postdeploy_retries, postdeploy_retry_delay)

            #
            # postdeploy check complete
            #
            if not post_deploy_check_passed:
                error_message = f"deployment failed for {resource['name']} after post-deploy checks."
                self.logger.error(error_message)
                raise Exception(error_message)

            if not dry_run:
                self.logger.info(f"successfully deployed {resource['name']}")
