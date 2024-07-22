import os, yaml, json, base64
from .utils import pull_providers, catch_error_and_exit
from jinja2 import Environment, FileSystemLoader, select_autoescape
from jinja2.utils import markupsafe
from jinja2 import TemplateError

# jinja filters

def from_json(value):
    return json.loads(value)

def base64_encode(value):
    return base64.b64encode(value.encode()).decode()

def merge_lists(list1, list2):
    if not isinstance(list1, list) or not isinstance(list2, list):
        raise ValueError("Both arguments must be lists")

    # Convert lists to sets of JSON strings to handle unhashable types
    set1 = set(json.dumps(item, sort_keys=True) for item in list1)
    set2 = set(json.dumps(item, sort_keys=True) for item in list2)

    # Merge sets
    merged_set = set1 | set2

    # Convert back to list of dictionaries
    merged_list = [json.loads(item) for item in merged_set]
    return merged_list

def generate_patch_document(properties):
    """
    Generates a patch document for the given resource, this is designed for the AWS Cloud Control API, which requires 
    a patch document to update resources.
    """
    patch_doc = []
    for key, value in properties.items():
        patch_doc.append({"op": "add", "path": f"/{key}", "value": value})
    
    return json.dumps(patch_doc)

# END jinja filters

def render_value(env, value, context):
    if isinstance(value, str):
        try:
            template = env.from_string(value)
            rendered = template.render(**context)
            if rendered in ['True', 'False']:
                return rendered.replace('True', 'true').replace('False', 'false')
            return rendered
        except TemplateError as e:
            print(f"Error rendering template: {e}")
            return value
    elif isinstance(value, dict):
        return {k: render_value(env, v, context) for k, v in value.items()}
    elif isinstance(value, list):
        return [render_value(env, item, context) for item in value]
    else:
        return value

def render_globals(env, vars, global_vars, stack_env, stack_name):
    global_context = {'stack_env': stack_env, 'stack_name': stack_name}
    global_context.update(vars)

    for global_var in global_vars:
        rendered_value = render_value(env, global_var['value'], global_context)
        if not rendered_value:
            raise ValueError(f"Global variable '{global_var['name']}' cannot be empty.")
        global_context[global_var['name']] = rendered_value

    return global_context

def render_properties(env, resource_props, global_context, logger):

    prop_context = {}
    for prop in resource_props:
        try:
            if 'value' in prop:
                prop_context[prop['name']] = render_value(env, prop['value'], global_context)
            elif 'values' in prop:
                env_value = prop['values'].get(global_context['stack_env'], {}).get('value')
                if env_value is not None:
                    prop_context[prop['name']] = render_value(env, env_value, global_context)
                else:
                    catch_error_and_exit(f"No value specified for property '{prop['name']}' in stack_env '{global_context['stack_env']}'.", logger)

            if 'merge' in prop:
                merged_list = prop_context.get(prop['name'], [])
                for merge_item in prop['merge']:
                    if merge_item in global_context:
                        merged_list = merge_lists(merged_list, global_context[merge_item])
                    else:
                        catch_error_and_exit(f"Merge item '{merge_item}' not found in global context.", logger)
                prop_context[prop['name']] = merged_list

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
    env.filters['merge_lists'] = merge_lists
    env.filters['base64_encode'] = base64_encode
    env.filters['generate_patch_document'] = generate_patch_document
    logger.debug("custom Jinja filters registered: %s", env.filters.keys())
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
