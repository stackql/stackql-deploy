from jinja2 import Environment, FileSystemLoader, select_autoescape
import os, yaml

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
        # Execute the test query
        test_result = self.stackql.execute(rendered_test_iql)
        self.logger.debug(f"test query result for [{resource['name']}]: {test_result}")
            
        # Check test results
        if not test_result or 'count' not in test_result[0] or int(test_result[0]['count']) != 1:
            self.logger.error(f"test failed for [{resource['name']}].")
            return False
        self.logger.info(f"test passed for [{resource['name']}].")
        return True


    def run(self, dry_run, on_failure):
        global_context = self._render_globals()  # Step 1

        for resource in self.manifest['resources']:
            prop_context = self._render_properties(resource['props'], global_context)  # Step 2 & 3
            full_context = {**self.vars, **global_context, **prop_context}  # Combine all contexts

            # render deploy query
            deploy_template_path = os.path.join(self.stack_dir, resource['deploy'])
            deploy_template = self.env.get_template(deploy_template_path)
            rendered_deploy_iql = deploy_template.render(full_context)

            # render test query if defined
            if 'test' in resource:
                test_template_path = os.path.join(self.stack_dir, resource['test'])
                test_template = self.env.get_template(test_template_path)
                rendered_test_iql = test_template.render(full_context)

            if dry_run:
                self.logger.info(f"dry run deploy for [{resource['name']}]:\n\n{rendered_deploy_iql}\n")
                self.logger.info(f"dry run test for [{resource['name']}]:\n\n{rendered_test_iql}\n") if 'test' in resource else None
            else:
                # run the deploy command
                self.logger.info(f"deploying [{resource['name']}]...")
                msg = self.stackql.executeStmt(rendered_deploy_iql)
                self.logger.info(f"result: {msg}")
                # run the test
                if 'test' in resource:
                    self.logger.info(f"running test for [{resource['name']}]...")
                    test_success = self.run_test(resource, rendered_test_iql)
                    if not test_success and on_failure == 'rollback':
                        self.logger.info("Rolling back deployment...")
                        # self.rollback(resource, full_context)  # You need to define the rollback method
                
                # Run the IQL command
                pass  # Execute your IQL command here
                # Handle tests, teardown, etc., similarly by rendering their templates
