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

    def run(self, dry_run, on_failure):
        global_context = self._render_globals()  # Step 1

        for resource in self.manifest['resources']:
            prop_context = self._render_properties(resource['props'], global_context)  # Step 2 & 3
            full_context = {**self.vars, **global_context, **prop_context}  # Combine all contexts

            iql_template_path = os.path.join(self.stack_dir, resource['deploy'])
            template = self.env.get_template(iql_template_path)
            rendered_iql = template.render(full_context)

            if dry_run:
                self.logger.info(f"dry run output for [{resource['name']}]:\n{rendered_iql}")
            else:
                self.logger.info(rendered_iql)
                
                # Run the IQL command
                pass  # Execute your IQL command here
                # Handle tests, teardown, etc., similarly by rendering their templates
