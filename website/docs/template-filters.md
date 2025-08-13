---
id: template-filters
title: Template Filters
hide_title: false
hide_table_of_contents: false
description: Custom and built-in Jinja2 filters available in StackQL Deploy for template processing
tags: []
draft: false
unlisted: false
---

import File from '/src/components/File';

# Template Filters

StackQL Deploy leverages Jinja2 templating capabilities and extends them with custom filters specifically designed for infrastructure provisioning use cases. These filters help transform data between formats, encode values, generate specialized document formats, and perform other common operations required in IaC configurations.

## Available Filters

### `from_json`

Converts a JSON string to a Python dictionary or list. This is commonly used to enable iteration over complex data structures in templates.

**Example usage:**

```sql
{% for network_interface in network_interfaces | from_json %}
INSERT INTO google.compute.instances 
 (
  /* fields... */
 ) 
 SELECT
'{{ instance_name_prefix }}-{{ loop.index }}',
/* other values... */
'[ {{ network_interface | tojson }} ]';
{% endfor %}
```

### `tojson`

A built-in Jinja2 filter that converts a Python dictionary or list into a JSON string. Often used in conjunction with `from_json` when working with complex data structures.

**Example usage:**

```sql
'[ {{ network_interface | tojson }} ]'
```

### `generate_patch_document`

Generates a patch document according to [RFC6902](https://datatracker.ietf.org/doc/html/rfc6902), primarily designed for the AWS Cloud Control API which requires patch documents for resource updates.

**Example usage:**

```sql
update aws.s3.buckets 
set data__PatchDocument = string('{{ {
    "NotificationConfiguration": transfer_notification_config
    } | generate_patch_document }}') 
WHERE 
region = '{{ region }}' 
AND data__Identifier = '{{ bucket_name }}';
```

### `base64_encode`

Encodes a string as base64, which is commonly required for certain API fields that accept binary data.

**Example usage:**

```sql
INSERT INTO aws.ec2.instances (
 /* fields... */
 UserData,
 region
)
SELECT 
 /* values... */
 '{{ user_data | base64_encode }}',
 '{{ region }}';
```

### `sql_list`

Converts a Python list or a JSON array string into a SQL-compatible list format with proper quoting, suitable for use in SQL IN clauses.

**Example usage:**

```sql
SELECT * FROM aws.ec2.instances
WHERE region = '{{ region }}'
AND InstanceId IN {{ instance_ids | sql_list }}
```

### `sql_escape`

Escapes a string for use as a SQL string literal by doubling any single quotes. This is particularly useful for nested SQL statements where quotes need special handling.

**Example usage:**

```sql
INSERT INTO snowflake.sqlapi.statements (
data__statement,
/* other fields... */
)
SELECT 
'{{ statement | sql_escape }}',
/* other values... */
;
```

### `merge_lists`

Merges two lists (or JSON-encoded list strings) into a single list with unique items.

**Example usage:**

```sql
{% set combined_policies = default_policies | merge_lists(custom_policies) %}
INSERT INTO aws.iam.policies (
  /* fields... */
  PolicyDocument,
  /* other fields... */
)
SELECT
  /* values... */
  '{{ combined_policies | tojson }}',
  /* other values... */
;
```

### `merge_objects`

Merges two dictionaries (or JSON-encoded object strings) into a single dictionary. In case of duplicate keys, values from the second dictionary take precedence.

**Example usage:**

```sql
{% set complete_config = base_config | merge_objects(environment_specific_config) %}
INSERT INTO aws.lambda.functions (
  /* fields... */
  Environment,
  /* other fields... */
)
SELECT
  /* values... */
  '{{ complete_config | tojson }}',
  /* other values... */
;
```

## Global Functions

### `uuid`

Generates a random UUID (version 4). Useful for creating unique identifiers.

**Example usage:**

```sql
INSERT INTO aws.s3.buckets (
  /* fields... */
  data__BucketName,
  /* other fields... */
)
SELECT
  /* values... */
  '{{ stack_name }}-{{ uuid() }}',
  /* other values... */
;
```

## Filter Chaining

Filters can be chained together to perform multiple transformations in sequence:

```sql
'{{ user_config | from_json | merge_objects(default_config) | tojson | base64_encode }}'
```

## Custom Filter Development

The StackQL Deploy filtering system is extensible. If you need additional filters for your specific use case, you can contribute to the project by adding new filters to the `lib/filters.py` file.