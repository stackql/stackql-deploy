import os, yaml, json
from .utils import pull_providers, catch_error_and_exit
from jinja2 import Environment, FileSystemLoader, select_autoescape
from jinja2.utils import markupsafe
from jinja2 import TemplateError

def from_json(value):
    return json.loads(value)

def render_globals(env, vars, global_vars, stack_env, stack_name):
    # Establish the context with stack environment and stack name, and other vars if needed
    global_context = {'stack_env': stack_env, 'stack_name': stack_name}
    global_context.update(vars)

    def render_value(value, context):
        """Handles recursive rendering of values that might be strings, lists, or dictionaries."""
        if isinstance(value, str):
            try:
                # Render the string using Jinja2 with the current context to resolve any templates
                template = env.from_string(value)
                return template.render(**context)  # Use **context to spread the context dictionary
            except TemplateError as e:
                print(f"Error rendering template: {e}")
                return value
        elif isinstance(value, dict):
            # Recursively process and serialize each dictionary after processing
            processed_dict = {k: render_value(v, context) for k, v in value.items()}
            return json.dumps(processed_dict, ensure_ascii=False).replace('True', 'true').replace('False', 'false')
        elif isinstance(value, list):
            # First resolve templates in list items, then serialize the list as a whole
            return [render_value(item, context) for item in value]
        else:
            return value

    # Update the global context with the rendered results
    for global_var in global_vars:
        global_context[global_var['name']] = render_value(global_var['value'], global_context)

    return global_context

def render_properties(env, resource_props, global_context, logger):

    def render_value(value, context):
        """Handles recursive rendering of values that might be strings, lists, or dictionaries."""
        if isinstance(value, str):
            try:
                template = env.from_string(value)
                rendered = template.render(context)
                return rendered.replace('True', 'true').replace('False', 'false')
            except TemplateError as e:
                print(f"Error rendering template: {e}")
                return value
        elif isinstance(value, dict):
            rendered_dict = {k: render_value(v, context) for k, v in value.items()}
            return rendered_dict
        elif isinstance(value, list):
            processed_list = [render_value(item, context) for item in value]
            return processed_list
        else:
            return value
   
    prop_context = {}
    for prop in resource_props:
        try:
            if 'value' in prop:
                prop_context[prop['name']] = render_value(prop['value'], global_context)
            elif 'values' in prop:
                env_value = prop['values'].get(global_context['stack_env'], {}).get('value')
                if env_value is not None:
                    prop_context[prop['name']] = render_value(env_value, global_context)
                else:
                    catch_error_and_exit(f"No value specified for property '{prop['name']}' in stack_env '{global_context['stack_env']}'.", logger)
        except Exception as e:
            catch_error_and_exit(f"Failed to render property '{prop['name']}']: {e}", logger)
    
    # Serialize lists and dictionaries to JSON strings
    for key, value in prop_context.items():
        if isinstance(value, (list, dict)):
            prop_context[key] = json.dumps(value).replace('True', 'true').replace('False', 'false')
    
    return prop_context

#
# exported functions
#

def load_manifest(stack_dir, logger):
    try:
        # Load and parse the stackql_manifest.yml
        with open(os.path.join(stack_dir, 'stackql_manifest.yml')) as f:
            return yaml.safe_load(f)
    except Exception as e:
        catch_error_and_exit("failed to load manifest: " + str(e), logger)

def setup_environment(stack_dir, logger):
    if not os.path.exists(stack_dir):
        catch_error_and_exit("stack directory does not exist.", logger)
    env = Environment(
        loader=FileSystemLoader(os.getcwd()),
        autoescape=False
    )
    env.filters['from_json'] = from_json
    return env

def get_global_context_and_providers(env, manifest, vars, stack_env, stack_name, stackql, logger):
    # Extract the global variables from the manifest and include stack_env
    try:
        global_vars = manifest.get('globals', [])
        global_context = render_globals(env, vars, global_vars, stack_env, stack_name)
        providers = manifest.get('providers', [])
        pull_providers(providers, stackql, logger)
        return global_context, providers
    except Exception as e:
        catch_error_and_exit("failed to prepare the context: " + str(e), logger)

def get_full_context(env, global_context, resource, logger):
    try:
        resource_props = resource.get('props', {})
        logger.debug(f"rendering properties for {resource['name']}...")
        prop_context = render_properties(env, resource_props, global_context, logger)
        full_context = {**global_context, **prop_context}
        logger.debug(f"full context: {full_context}")
        return full_context
    except Exception as e:
        catch_error_and_exit(f"failed to render properties for {resource.get('name', 'unknown')}: " + str(e), logger)
