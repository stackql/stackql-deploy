import os, yaml, json, base64
from .utils import pull_providers, catch_error_and_exit
from jinja2 import Environment, FileSystemLoader, select_autoescape
from jinja2.utils import markupsafe
from jinja2 import TemplateError

# jinja filters

def from_json(value):
    return json.loads(value)

# def to_json_string(value):
#     return json.dumps(json.loads(value))

# def remove_single_quotes(value):
#     return str(value).replace("'", "")

def base64_encode(value):
    return base64.b64encode(value.encode()).decode()

def merge_lists(tags1, tags2):
    combined_tags = tags1 + tags2
    combined_tags_json = json.dumps(combined_tags)
    return combined_tags_json

# END jinja filters

def render_globals(env, vars, global_vars, stack_env, stack_name):
    global_context = {'stack_env': stack_env, 'stack_name': stack_name}
    global_context.update(vars)

    def render_value(value, context):
        if isinstance(value, str):
            try:
                template = env.from_string(value)
                return template.render(**context)
            except TemplateError as e:
                print(f"Error rendering template: {e}")
                return value
        elif isinstance(value, dict):
            return {k: render_value(v, context) for k, v in value.items()}
        elif isinstance(value, list):
            return [render_value(item, context) for item in value]
        else:
            return value

    for global_var in global_vars:
        global_context[global_var['name']] = render_value(global_var['value'], global_context)

    return global_context

def render_properties(env, resource_props, global_context, logger):

    def render_value(value, context):
        if isinstance(value, str):
            try:
                template = env.from_string(value)
                # rendered = template.render(context)
                rendered = template.render(**context)
                # deal with boolean values
                if rendered in ['True', 'False']:
                    return rendered.replace('True', 'true').replace('False', 'false')
                return rendered
            except TemplateError as e:
                print(f"Error rendering template: {e}")
                return value
        elif isinstance(value, dict):
            return {k: render_value(v, context) for k, v in value.items()}
        elif isinstance(value, list):
            return [render_value(item, context) for item in value]
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
    # env.filters['to_json_string'] = to_json_string
    # env.filters['remove_single_quotes'] = remove_single_quotes
    env.filters['merge_lists'] = merge_lists
    env.filters['base64_encode'] = base64_encode
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
