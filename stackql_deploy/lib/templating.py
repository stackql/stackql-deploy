import os


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

def render_queries(env, queries, context):
    """Render queries with context using Jinja2."""
    rendered_queries = {}
    for key, query in queries.items():
        template = env.from_string(query)
        rendered_queries[key] = template.render(context)
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
    template_path = os.path.join(stack_dir, doc_key, f"{resource['name']}.iql")
    if not os.path.exists(template_path):
        if fail_on_error:
            logger.error(f"query file not found: {template_path}")
            raise
        else:
            return {}, {}
    try:
        query_templates, query_options = load_sql_queries(template_path)
        queries = render_queries(env, query_templates, full_context)
        logger.debug(f"rendered queries: {queries}")
        logger.debug(f"query options: {query_options}")
        return queries, query_options
    except Exception as e:
        logger.error(f"failed to load or render queries for {resource['name']}: " + str(e))
        raise