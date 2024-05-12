import os, yaml, json
from .utils import pull_providers, catch_error_and_exit
from jinja2 import Environment, FileSystemLoader, select_autoescape
from jinja2.utils import markupsafe
from jinja2 import TemplateError

def render_globals(env, vars, global_vars, stack_env, stack_name):
    # Establish the context with stack environment and stack name, and other vars if needed
    global_context = {'stack_env': stack_env, 'stack_name': stack_name}

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
            processed_list = [render_value(item, context) for item in value]
            # Ensure each item is treated as a resolved string before forming the JSON array
            return '[' + ', '.join(processed_list) + ']'
        else:
            return value

    # Update the global context with the rendered results
    for global_var in global_vars:
        global_context[global_var['name']] = render_value(global_var['value'], global_context)

    return global_context

def render_properties(env, resource_props, global_context, logger):
    prop_context = {}
    for prop in resource_props:
        try:
            if 'value' in prop:
                if isinstance(prop['value'], (dict, list)):
                    # Convert dict or list directly to JSON string
                    json_string = json.dumps(prop['value'], separators=(',', ':')).replace('True', 'true').replace('False', 'false')
                    template = env.from_string(json_string)
                    rendered_json_string = template.render(global_context)
                    prop_context[prop['name']] = rendered_json_string
                else:
                    # Render non-dict/list values as regular strings
                    template = env.from_string(str(prop['value']))
                    # rendered_value = template.render(globals=global_context)
                    rendered_value = template.render(global_context)
                    prop_context[prop['name']] = rendered_value
            elif 'values' in prop:
                env_value = prop['values'].get(global_context['stack_env'], {}).get('value')
                if env_value is not None:
                    if isinstance(env_value, (dict, list)):
                        json_string = json.dumps(env_value, separators=(',', ':')).replace('True', 'true').replace('False', 'false')
                        prop_context[prop['name']] = json_string
                    else:
                        template = env.from_string(str(env_value))
                        # rendered_value = template.render(globals=global_context)
                        rendered_value = template.render(global_context)
                        prop_context[prop['name']] = rendered_value
                else:
                    catch_error_and_exit(f"No value specified for property '{prop['name']}' in stack_env '{global_context['stack_env']}'.", logger)
        except Exception as e:
            catch_error_and_exit(f"Failed to render property '{prop['name']}': {e}", logger)
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
