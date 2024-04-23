import os, yaml, json
from .utils import pull_providers, catch_error_and_exit
from jinja2 import Environment, FileSystemLoader, select_autoescape
from jinja2.utils import markupsafe

def render_globals(env, vars, global_vars, stack_env):
    # Render globals with vars and include the stack_env as a special variable
    global_context = {'stack_env': stack_env}
    # Render each global variable defined in the manifest
    for global_var in global_vars:
        # Assume each global_var is a dictionary with 'name' and 'value' keys
        template = env.from_string(global_var['value'])
        global_context[global_var['name']] = template.render(globals=global_context, vars=vars)
    return global_context

def render_properties(env, resource_props, global_context, logger):
    # Render properties with globals and vars
    prop_context = {}
    for prop in resource_props:
        try:
            if 'value' in prop:
                # Check if value is a dict, and convert it to a JSON string
                if isinstance(prop['value'], (dict, list)):
                    prop_context[prop['name']] = markupsafe.Markup(json.dumps(prop['value'], separators=(',', ':')))
                else:
                    # Single value for all environments
                    template = env.from_string(str(prop['value']))
                    prop_context[prop['name']] = template.render(globals=global_context)
            elif 'values' in prop:
                # Environment-specific values
                env_value = prop['values'].get(global_context['stack_env'], {}).get('value')
                if env_value is not None:
                    if isinstance(env_value, (dict, list)):
                        prop_context[prop['name']] =  markupsafe.Markup(json.dumps(prop['value'], separators=(',', ':')))
                    else:
                        template = env.from_string(str(env_value))
                        prop_context[prop['name']] = template.render(globals=global_context)
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
        autoescape=select_autoescape()
    )
    return env

def get_global_context_and_providers(env, manifest, vars, stack_env, stackql, logger):
    # Extract the global variables from the manifest and include stack_env
    try:
        global_vars = manifest.get('globals', [])
        global_context = render_globals(env, vars, global_vars, stack_env)
        providers = manifest.get('providers', [])
        pull_providers(providers, stackql, logger)
        return global_context, providers
    except Exception as e:
        catch_error_and_exit("failed to prepare the context: " + str(e), logger)

def get_full_context(env, global_context, resource, logger):
    try:
        resource_props = resource.get('props', {})
        prop_context = render_properties(env, resource_props, global_context, logger)
        full_context = {**global_context, **prop_context}
        logger.debug(f"full context: {full_context}")
        return full_context
    except Exception as e:
        catch_error_and_exit(f"failed to render properties for {resource.get('name', 'unknown')}: " + str(e), logger)
