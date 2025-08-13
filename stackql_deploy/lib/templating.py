# lib/templating.py
import json
import os
from .utils import catch_error_and_exit
from jinja2 import TemplateError
from pprint import pformat

def parse_anchor(anchor, logger):
    """Parse anchor to extract key and options."""
    parts = anchor.split(',')
    key = parts[0].strip()
    options = {}
    for part in parts[1:]:
        if '=' in part:
            option_key, option_value = part.split('=')
            options[option_key.strip()] = int(option_value.strip())
    return key, options

def is_json(myjson, logger):
    try:
        obj = json.loads(myjson)
        return isinstance(obj, (dict, list))  # Only return True for JSON objects or arrays
    except ValueError:
        return False

def render_queries(res_name, env, queries, context, logger):
    rendered_queries = {}
    for key, query in queries.items():
        logger.debug(f"(templating.render_queries) [{res_name}] [{key}] query template:\n\n{query}\n")
        try:
            temp_context = context.copy()

            for ctx_key, ctx_value in temp_context.items():
                if isinstance(ctx_value, str) and is_json(ctx_value, logger):
                    properties = json.loads(ctx_value)
                    # Serialize JSON ensuring booleans are lower case and using correct JSON syntax
                    json_str = json.dumps(
                        properties, ensure_ascii=False, separators=(',', ':')
                    ).replace('True', 'true').replace('False', 'false')
                    # Correctly format JSON to use double quotes and pass directly since template handles quoting
                    # json_str = json_str.replace("'", "\\'")  # escape single quotes if any within strings
                    temp_context[ctx_key] = json_str
                # No need to alter non-JSON strings, assume the template handles them correctly

            template = env.from_string(query)
            rendered_query = template.render(temp_context)
            logger.debug(f"(templating.render_queries) [{res_name}] [{key}] rendered query:\n\n{rendered_query}\n")
            rendered_queries[key] = rendered_query

        except TemplateError as e:
            raise RuntimeError(f"(templating.render_queries) error rendering query for [{res_name}] [{key}]: {e}")
        except json.JSONDecodeError:
            continue  # Skip non-JSON content

    return rendered_queries

def load_sql_queries(file_path, logger):
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
                    anchor_key, anchor_options = parse_anchor(current_anchor, logger)
                    queries[anchor_key] = ''.join(query_buffer).strip()
                    options[anchor_key] = anchor_options
                    query_buffer = []
                # Set the new anchor
                current_anchor = line[line.find('/*+') + 3:line.find('*/')].strip()
            else:
                query_buffer.append(line)

        # Store the last query if any
        if current_anchor and query_buffer:
            anchor_key, anchor_options = parse_anchor(current_anchor, logger)
            queries[anchor_key] = ''.join(query_buffer).strip()
            options[anchor_key] = anchor_options

    return queries, options

#
# exported fuctions
#

def get_queries(env, stack_dir, doc_key, resource, full_context, logger):
    """Returns an object with query templates, rendered queries, and options for a resource."""
    result = {}

    if resource.get('file'):
        template_path = os.path.join(stack_dir, doc_key, resource['file'])
    else:
        template_path = os.path.join(stack_dir, doc_key, f"{resource['name']}.iql")

    if not os.path.exists(template_path):
        catch_error_and_exit(f"(templating.get_queries) query file not found: {template_path}", logger)

    try:
        query_templates, query_options = load_sql_queries(template_path, logger)
        rendered_queries = render_queries(resource['name'], env, query_templates, full_context, logger)

        for anchor, template in query_templates.items():
            # fix backward compatibility for preflight and postdeploy queries
            if anchor == 'preflight':
                anchor = 'exists'
            elif anchor == 'postdeploy':
                anchor = 'statecheck'
            # end backward compatibility fix
            result[anchor] = {
                "template": template,
                "rendered": rendered_queries.get(anchor, ""),
                "options": {
                    "retries": query_options.get(anchor, {}).get('retries', 1),
                    "retry_delay": query_options.get(anchor, {}).get('retry_delay', 0)
                }
            }

        formatted_result = pformat(result, width=120, indent=2)
        logger.debug(f"(templating.get_queries) queries for [{resource['name']}]:\n{formatted_result}")
        return result
    except Exception as e:
        catch_error_and_exit(
            f"(templating.get_queries) failed to load or render queries for [{resource['name']}]: {str(e)}",
            logger
        )

def render_inline_template(env, resource_name, template_string, full_context, logger):
    """
    Renders a single template string using the provided context.
    Similar to get_queries but for inline templates rather than files.
    """
    logger.debug(f"(templating.render_inline_template) [{resource_name}] template:\n\n{template_string}\n")

    try:
        # Process the context the same way as in render_queries
        temp_context = full_context.copy()

        for ctx_key, ctx_value in temp_context.items():
            if isinstance(ctx_value, str) and is_json(ctx_value, logger):
                properties = json.loads(ctx_value)
                # Serialize JSON ensuring booleans are lower case and using correct JSON syntax
                json_str = json.dumps(
                    properties, ensure_ascii=False, separators=(',', ':')
                ).replace('True', 'true').replace('False', 'false')
                # Correctly format JSON to use double quotes and pass directly since template handles quoting
                # json_str = json_str.replace("'", "\\'")  # escape single quotes if any within strings
                temp_context[ctx_key] = json_str

        # Render the template
        template = env.from_string(template_string)
        rendered_template = template.render(temp_context)

        logger.debug(
            f"(templating.render_inline_template) [{resource_name}] rendered template:"
            f"\n\n{rendered_template}\n"
        )
        return rendered_template

    except TemplateError as e:
        raise RuntimeError(f"(templating.render_inline_template) error rendering template for [{resource_name}]: {e}")
    except json.JSONDecodeError as e:
        # Handle JSON errors more gracefully
        logger.warning(f"(templating.render_inline_template) JSON decode error in context for [{resource_name}]: {e}")
        # Try rendering anyway, might work with non-JSON parts of the context
        template = env.from_string(template_string)
        rendered_template = template.render(temp_context)
        return rendered_template
