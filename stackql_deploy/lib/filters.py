# lib/filters.py
import os
import json
import base64
import uuid
from jinja2 import Environment, FileSystemLoader
from .utils import catch_error_and_exit

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

def sql_list(input_data):
    # If the input is already a string representation of a list, parse it
    if isinstance(input_data, str):
        try:
            import json
            # Parse the string as JSON array
            python_list = json.loads(input_data)
        except json.JSONDecodeError:
            # If it's not valid JSON, treat it as a single item
            python_list = [input_data]
    else:
        python_list = input_data

    # Handle empty list case
    if not python_list:
        return '(NULL)'

    # Convert each item to string, wrap in quotes, join with commas
    quoted_items = [f"'{str(item)}'" for item in python_list]
    return f"({','.join(quoted_items)})"

def sql_escape(value):
    """
    Escapes a string for use as a SQL string literal by doubling any single quotes.
    This is useful for nested SQL statements where single quotes need to be escaped.
    Args:
        value: The string to escape
    Returns:
        The escaped string with single quotes doubled
    """
    if value is None:
        return None

    if not isinstance(value, str):
        value = str(value)

    return value.replace("'", "''")

#
# exported functions
#

def setup_environment(stack_dir, logger):
    logger.debug("(config.setup_environment) setting up environment...")
    if not os.path.exists(stack_dir):
        catch_error_and_exit("(config.setup_environment) stack directory does not exist.", logger)
    env = Environment(
        loader=FileSystemLoader(os.getcwd()),
        autoescape=False
    )
    env.filters['from_json'] = from_json
    env.filters['base64_encode'] = base64_encode
    env.filters['merge_lists'] = merge_lists
    env.filters['generate_patch_document'] = generate_patch_document
    env.filters['sql_list'] = sql_list
    env.filters['sql_escape'] = sql_escape
    env.globals['uuid'] = lambda: str(uuid.uuid4())
    logger.debug("custom Jinja filters registered: %s", env.filters.keys())
    return env
