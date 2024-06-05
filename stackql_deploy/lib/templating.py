import json
import os
import re
from .utils import catch_error_and_exit
from jinja2 import TemplateError
from jinja2.utils import markupsafe

def parse_anchor(anchor):
    """Parse anchor to extract key and options."""
    parts = anchor.split(',')
    key = parts[0].strip()
    options = {}
    for part in parts[1:]:
        if '=' in part:
            option_key, option_value = part.split('=')
            options[option_key.strip()] = int(option_value.strip())
    return key, options

def is_json(myjson):
    try:
        obj = json.loads(myjson)
        return isinstance(obj, (dict, list))  # Only return True for JSON objects or arrays
    except ValueError:
        return False

def render_queries(env, queries, context):
    rendered_queries = {}
    for key, query in queries.items():
        try:
            temp_context = context.copy()

            for ctx_key, ctx_value in temp_context.items():
                if isinstance(ctx_value, str) and is_json(ctx_value):
                    properties = json.loads(ctx_value)
                    # Serialize JSON ensuring booleans are lower case and using correct JSON syntax
                    json_str = json.dumps(properties, ensure_ascii=False, separators=(',', ':')).replace('True', 'true').replace('False', 'false')
                    # Correctly format JSON to use double quotes and pass directly since template handles quoting
                    json_str = json_str.replace("'", "\\'")  # escape single quotes if any within strings
                    temp_context[ctx_key] = json_str
                # No need to alter non-JSON strings, assume the template handles them correctly

            template = env.from_string(query)
            rendered_query = template.render(temp_context)
            rendered_queries[key] = rendered_query

        except TemplateError as e:
            raise RuntimeError(f"Error rendering query '{key}': {e}")
        except json.JSONDecodeError:
            continue  # Skip non-JSON content

    return rendered_queries

def load_sql_queries(file_path):
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
                    anchor_key, anchor_options = parse_anchor(current_anchor)
                    queries[anchor_key] = ''.join(query_buffer).strip()
                    options[anchor_key] = anchor_options
                    query_buffer = []
                # Set the new anchor
                current_anchor = line[line.find('/*+') + 3:line.find('*/')].strip()
            else:
                query_buffer.append(line)
        
        # Store the last query if any
        if current_anchor and query_buffer:
            anchor_key, anchor_options = parse_anchor(current_anchor)
            queries[anchor_key] = ''.join(query_buffer).strip()
            options[anchor_key] = anchor_options

    return queries, options

#
# exported fuctions
#

def get_queries(env, stack_dir, doc_key, resource, full_context, fail_on_error, logger):
    """returns rendered queries and query options for a resource."""
    if resource.get('file'):
        template_path = os.path.join(stack_dir, doc_key, resource['file'])
    else:
        template_path = os.path.join(stack_dir, doc_key, f"{resource['name']}.iql")
    if not os.path.exists(template_path):
        if fail_on_error:
            catch_error_and_exit(f"query file not found: {template_path}", logger)
        else:
            return {}, {}
    try:
        query_templates, query_options = load_sql_queries(template_path)
        queries = render_queries(env, query_templates, full_context)
        logger.debug(f"rendered queries: {queries}")
        logger.debug(f"query options: {query_options}")
        return queries, query_options
    except Exception as e:
        catch_error_and_exit(f"failed to load or render queries for {resource['name']}: " + str(e), logger)
