import os, yaml, json, base64, pprint
import sys
from .utils import pull_providers, catch_error_and_exit
from jinja2 import Environment, FileSystemLoader, TemplateError, select_autoescape
from jinja2.utils import markupsafe

# jinja filters

def from_json(value):
    return json.loads(value)

def base64_encode(value):
    return base64.b64encode(value.encode()).decode()

def merge_lists(list1, list2):
    # Helper function to ensure we have Python lists, not JSON strings
    def ensure_list(input_data):
        if isinstance(input_data, str):
            try:
                # Attempt to decode a JSON string
                decoded = json.loads(input_data)
                if isinstance(decoded, list):
                    return decoded
            except json.JSONDecodeError:
                pass  # If it's not a JSON string, keep it as a string
        elif isinstance(input_data, list):
            return input_data
        raise ValueError("(config.merge_lists) input must be a list or a JSON-encoded list string")

    # Ensure both inputs are lists
    list1 = ensure_list(list1)
    list2 = ensure_list(list2)

    # Convert lists to sets of JSON strings to handle unhashable types
    set1 = set(json.dumps(item, sort_keys=True) for item in list1)
    set2 = set(json.dumps(item, sort_keys=True) for item in list2)

    # Merge sets
    merged_set = set1 | set2

    # Convert back to list of dictionaries or original items
    merged_list = [json.loads(item) for item in merged_set]
    return merged_list

def merge_objects(obj1, obj2):
    # Helper function to ensure we have Python dicts, not JSON strings
    def ensure_dict(input_data):
        if isinstance(input_data, str):
            try:
                # Attempt to decode a JSON string
                decoded = json.loads(input_data)
                if isinstance(decoded, dict):
                    return decoded
            except json.JSONDecodeError:
                pass  # If it's not a JSON string, keep it as a string
        elif isinstance(input_data, dict):
            return input_data
        raise ValueError("(config.merge_objects) input must be a dict or a JSON-encoded dict string")

    # Ensure both inputs are dicts
    obj1 = ensure_dict(obj1)
    obj2 = ensure_dict(obj2)

    # Merge the two dictionaries
    merged_obj = {**obj1, **obj2}

    return merged_obj

def generate_patch_document(properties):
    """
    Generates a patch document for the given resource. This is designed for the AWS Cloud Control API, which requires 
    a patch document to update resources.
    """
    patch_doc = []
    for key, value in properties.items():
        # Check if the value is already a string (indicating it's likely already JSON) and leave it as is
        if isinstance(value, str):
            try:
                # Try to parse the string to confirm it's a JSON object/array
                parsed_value = json.loads(value)
                patch_doc.append({"op": "add", "path": f"/{key}", "value": parsed_value})
            except json.JSONDecodeError:
                # If it's not a JSON string, treat it as a simple string value
                patch_doc.append({"op": "add", "path": f"/{key}", "value": value})
        else:
            # If it's not a string, add it as a JSON-compatible object
            patch_doc.append({"op": "add", "path": f"/{key}", "value": value})

    return json.dumps(patch_doc)

# END jinja filters

def to_sql_compatible_json(value):
    """
    Convert a Python object to a SQL-compatible format:
    - string -> string
    - int -> int
    - float -> float
    - dict -> json string
    - list -> json string
    - json string -> json string
    - boolean -> boolean (true, false are returned as is)
    
    Args:
        value: The Python object to be converted.
    
    Returns:
        A SQL-compatible format.
    """
    if isinstance(value, (int, float, bool)):
        # Return as-is if the value is an int, float, or boolean
        return value

    if isinstance(value, str):
        try:
            # Try to load the string as JSON to see if it's already a valid JSON string
            json.loads(value)
            return value  # It's a valid JSON string, return as-is
        except ValueError:
            # It's not a valid JSON string, so return it as a string
            return value

    if isinstance(value, (dict, list)):
        # Convert dicts and lists to JSON strings
        return json.dumps(value)

    # If the value doesn't match any of the above types, return it as-is
    return value

def render_value(env, value, context, logger):
    if isinstance(value, str):
        try:
            template = env.from_string(value)
            rendered = template.render(**context)
            if rendered in ['True', 'False']:
                return rendered.replace('True', 'true').replace('False', 'false')
            return rendered
        except TemplateError as e:
            print(f"(config.render_value) error rendering template: {e}")
            return value
    elif isinstance(value, dict):
        return {k: render_value(env, v, context, logger) for k, v in value.items()}
    elif isinstance(value, list):
        return [render_value(env, item, context, logger) for item in value]
    else:
        return value

def render_globals(env, vars, global_vars, stack_env, stack_name, logger):
    # Start with only the stack-specific variables in the context
    global_context = {'stack_env': stack_env, 'stack_name': stack_name}

    logger.debug("(config.render_globals) rendering global variables...")
    # Now render each global variable using the combined context of env vars and the current global context
    for global_var in global_vars:
        # Merge global_context with vars to create a complete context for rendering
        combined_context = {**vars, **global_context}
        
        # Render using the combined context
        rendered_value = render_value(env, global_var['value'], combined_context, logger)
        
        if not rendered_value:
            raise ValueError(f"(config.render_globals) global variable '{global_var['name']}' cannot be empty.")
        
        # Update the context with the rendered global variable
        logger.debug(f"(config.render_globals) setting global variable [{global_var['name']}] to {to_sql_compatible_json(rendered_value)}")
        global_context[global_var['name']] = to_sql_compatible_json(rendered_value)

    return global_context

def render_properties(env, resource_props, global_context, logger):
    prop_context = {}

    logger.debug("rendering properties...")
    for prop in resource_props:
        try:
            if 'value' in prop:
                rendered_value = render_value(env, prop['value'], global_context, logger)
                logger.debug(f"(config.render_properties) setting property [{prop['name']}] to {to_sql_compatible_json(rendered_value)}")
                prop_context[prop['name']] = to_sql_compatible_json(rendered_value)
            elif 'values' in prop:
                env_value = prop['values'].get(global_context['stack_env'], {}).get('value')
                if env_value is not None:
                    rendered_value = render_value(env, env_value, global_context, logger)
                    logger.debug(f"(config.render_properties) setting property [{prop['name']}] using value for {env_value} to {to_sql_compatible_json(rendered_value)}")
                    prop_context[prop['name']] = to_sql_compatible_json(rendered_value)
                else:
                    catch_error_and_exit(f"(config.render_properties) no value specified for property '{prop['name']}' in stack_env '{global_context['stack_env']}'.", logger)

            if 'merge' in prop:
                logger.debug(f"(config.render_properties) processing merge for [{prop['name']}]")
                base_value_rendered = prop_context.get(prop['name'], None)
                base_value = json.loads(base_value_rendered)
                base_value_type = type(base_value)
                logger.debug(f"(config.render_properties) base value for [{prop['name']}]: {base_value_rendered} (type: {base_value_type})")
                for merge_item in prop['merge']:
                    if merge_item in global_context:
                        merge_value_rendered = global_context[merge_item]
                        merge_value = json.loads(merge_value_rendered)
                        merge_value_type = type(merge_value)
                        logger.debug(f"(config.render_properties) [{prop['name']}] merge value [{merge_item}]: {merge_value_rendered} (type: {merge_value_type})")

                        # Determine if we're merging lists or objects
                        if isinstance(base_value, list) and isinstance(merge_value, list):
                            base_value = merge_lists(base_value, merge_value)
                        elif isinstance(base_value, dict) and isinstance(merge_value, dict):
                            base_value = merge_objects(base_value, merge_value)
                        elif base_value is None:
                            # Initialize base_value if it wasn't set before
                            if isinstance(merge_value, list):
                                base_value = merge_value
                            elif isinstance(merge_value, dict):
                                base_value = merge_value
                            else:
                                catch_error_and_exit(f"(config.render_properties) unsupported merge type for '{prop['name']}'", logger)
                        else:
                            catch_error_and_exit(f"(config.render_properties) type mismatch or unsupported merge operation on property '{prop['name']}'.", logger)
                    else:
                        catch_error_and_exit(f"(config.render_properties) merge item '{merge_item}' not found in global context.", logger)

                prop_context[prop['name']] = to_sql_compatible_json(base_value)

        except Exception as e:
            catch_error_and_exit(f"(config.render_properties) failed to render property '{prop['name']}']: {e}", logger)
    
    return prop_context

#
# exported functions
#

def load_manifest(stack_dir, logger):
    logger.debug("(config.load_manifest) loading manifest...")
    try:
        # Load and parse the stackql_manifest.yml
        with open(os.path.join(stack_dir, 'stackql_manifest.yml')) as f:
            return yaml.safe_load(f)
    except Exception as e:
        catch_error_and_exit("(config.load_manifest) failed to load manifest: " + str(e), logger)

def setup_environment(stack_dir, logger):
    logger.debug("(config.setup_environment) setting up environment...")
    if not os.path.exists(stack_dir):
        catch_error_and_exit("(config.setup_environment) stack directory does not exist.", logger)
    env = Environment(
        loader=FileSystemLoader(os.getcwd()),
        autoescape=False
    )
    env.filters['merge_lists'] = merge_lists
    env.filters['base64_encode'] = base64_encode
    env.filters['generate_patch_document'] = generate_patch_document
    env.filters['from_json'] = from_json
    logger.debug("custom Jinja filters registered: %s", env.filters.keys())
    return env

def get_global_context_and_providers(env, manifest, vars, stack_env, stack_name, stackql, logger):
    # Extract the global variables from the manifest and include stack_env
    logger.debug("(config.get_global_context_and_providers) getting global context and pulling providers...")
    try:
        global_vars = manifest.get('globals', [])
        global_context = render_globals(env, vars, global_vars, stack_env, stack_name, logger)
        providers = manifest.get('providers', [])
        pull_providers(providers, stackql, logger)
        return global_context, providers
    except Exception as e:
        catch_error_and_exit("(config.get_global_context_and_providers) failed to prepare the context: " + str(e), logger)

def get_full_context(env, global_context, resource, logger):
    logger.debug(f"(config.get_full_context) getting full context for {resource['name']}...")
    try:
        resource_props = resource.get('props', {})
        prop_context = render_properties(env, resource_props, global_context, logger)
        full_context = {**global_context, **prop_context}
 
        formatted_context = pprint.pformat(full_context, indent=1, width=sys.maxsize)
        logger.debug(f"(config.get_full_context) full context:\n{formatted_context}")

        return full_context
    except Exception as e:
        catch_error_and_exit(f"(config.get_full_context) failed to render properties for {resource.get('name', 'unknown')}: " + str(e), logger)
