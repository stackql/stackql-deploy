---
id: resource-query-files
title: Resource Query Files
hide_title: false
hide_table_of_contents: false
description: A quick overview of how to get started with StackQL Deploy, including basic concepts and the essential components of a deployment.
tags: []
draft: false
unlisted: false
---

import File from '/src/components/File';

Resource query files include the StackQL query templates to provision, de-provision, update and test resources in your stack.  Resource query files (`.iql` files) are located in the `resources` subdirectory of your project (stack) directory.  The `resources` section of the [`stackql_manifest.yml`](manifest-file) file is used to supply these templates with the correct values for a given environment at deploy time.

:::note

`.iql` is used as a file extension for StackQL query files by convention.  This convention originates from the original name for the StackQL project - InfraQL,  plus `.sql` was taken... 

:::

## Query types

A resource query file (`.iql` file) typically contains multiple StackQL queries.  Seperate queries are demarcated by query anchors (or hints), such as `/*+ create */` or `/*+ update */`.  These hints must be at the beginning of a line in the file, with the resepective query following on the subsequent lines.

:::tip

StackQL follows the ANSI standard for SQL with some custom extensions.  For more information on the StackQL grammar see the [StackQL docs](https://stackql.io/docs).

:::

The types of queries defined in resource files are detailed in the following sections.

### `preflight`

`preflight` queries are StackQL `SELECT` statements designed to test the existence of a resource by its designated identifier (does not test the desired state).  This is used to determine whether a `create` (`INSERT`) or `update` (`UPDATE`) is required.  A `preflight` query needs to return a single row with a single field named `count`.  A `count` value of `1` indicates that the resource exists, a value of `0` would indicate that the resource does not exist.

```sql
/*+ preflight */
SELECT COUNT(*) as count FROM google.compute.networks
WHERE name = '{{ vpc_name }}'
AND project = '{{ project }}'
```

### `create`

`create` queries are StackQL `INSERT` statements used to create resources that do not exist (in accordance with the `preflight` query).

```sql
/*+ create */
INSERT INTO google.compute.networks
(
 project,
 data__name,
 data__autoCreateSubnetworks,
 data__routingConfig
) 
SELECT
'{{ project }}',
'{{ vpc_name }}',
false,
'{"routingMode": "REGIONAL"}'
```

### `createorupdate`

`createorupdate` queries can be StackQL `INSERT` or `UPDATE` statements, these queries are used for idempotent resources (as per the given provider if supported), for example:

```sql
/*+ createorupdate */
INSERT INTO azure.network.virtual_networks(
   virtualNetworkName,
   resourceGroupName, 
   subscriptionId, 
   data__location,
   data__properties,
   data__tags   
)
SELECT
   '{{ vnet_name }}',
   '{{ resource_group_name }}',
   '{{ subscription_id }}',
   '{{ location }}',
   '{"addressSpace": {"addressPrefixes":["{{ vnet_cidr }}"]}}',
   '{{ global_tags }}'
```

:::tip

You can usually identify idempotent resources using the `SHOW METHODS` command for a given resource, the the below example you can see a `create_or_update` method mapped to StackQL `INSERT`:

```plaintext {12}
stackql  >>show methods in azure.network.virtual_networks;
|-------------------------------|--------------------------------|---------|                                                                                                               
|          MethodName           |         RequiredParams         | SQLVerb |                                                                                                               
|-------------------------------|--------------------------------|---------|                                                                                                               
| get                           | resourceGroupName,             | SELECT  |                                                                                                               
|                               | subscriptionId,                |         |                                                                                                               
|                               | virtualNetworkName             |         |                                                                                                               
|-------------------------------|--------------------------------|---------|                                                                                                               
| list                          | resourceGroupName,             | SELECT  |                                                                                                               
|                               | subscriptionId                 |         |                                                                                                               
|-------------------------------|--------------------------------|---------|                                                                                                               
| create_or_update              | resourceGroupName,             | INSERT  |                                                                                                               
|                               | subscriptionId,                |         |                                                                                                               
|                               | virtualNetworkName             |         |                                                                                                               
|-------------------------------|--------------------------------|---------|                                                                                                               
| delete                        | resourceGroupName,             | DELETE  |                                                                                                               
|                               | subscriptionId,                |         |                                                                                                               
|                               | virtualNetworkName             |         |                                                                                                               
|-------------------------------|--------------------------------|---------|                                                                                                               
| check_ip_address_availability | ipAddress, resourceGroupName,  | EXEC    |                                                                                                               
|                               | subscriptionId,                |         |                                                                                                               
|                               | virtualNetworkName             |         |                                                                                                               
|-------------------------------|--------------------------------|---------| 
```

:::

`createorupdate` queries can also be used if a resource is updating the state of a pre-existing resource, for example:

```sql
/*+ createorupdate */
update aws.s3.buckets 
set data__PatchDocument = string('{{ {
    "NotificationConfiguration": transfer_notification_config
    } | generate_patch_document }}') 
WHERE 
region = '{{ region }}' 
AND data__Identifier = '{{ transfer_bucket_name }}';
```

### `delete`

`delete` queries are StackQL `DELETE` statements used to de-provision resources in `teardown` operations.

```sql
/*+ delete */
DELETE FROM google.compute.networks
WHERE network = '{{ vpc_name }}' AND project = '{{ project }}'
```

### `postdeploy`

`postdeploy` queries are StackQL `SELECT` statements designed to test the desired state of a resource in an environment.  Similar to `preflight` queries, `postdeploy` queries must return a single row with a single column named `count` with a value of `1` (the resource meets the desired state tests) or `0` (the resource is not in the desired state).  As `postdeploy` queries are usually run after `create` or `update` queries, it may be necessary to retry the query to account for the time it takes for the resource to be created or updated by the provider.

```sql
/*+ postdeploy, retries=5, retry_delay=10 */
SELECT COUNT(*) as count FROM google.compute.networks
WHERE name = '{{ vpc_name }}'
AND project = '{{ project }}'
AND autoCreateSubnetworks = false
AND JSON_EXTRACT(routingConfig, '$.routingMode') = 'REGIONAL'
```

:::tip

Useful functions for testing the desired state of a resource include [`JSON_EQUAL`](https://stackql.io/docs/language-spec/functions/json/json_equal), [`JSON_EXTRACT`](https://stackql.io/docs/language-spec/functions/json/json_extract) and [`JSON_EACH`](https://stackql.io/docs/language-spec/functions/json/json_equal).

:::


### `exports`

`exports` queries are StackQL `SELECT` statements which export variables, typically used in subsequent (or dependant) resources.  Columns exported in `exports` queries need to be specified in the [`exports` section of the `stackql_manifest.yml` file](manifest-file#resourceexports).

```sql
/*+ exports */
SELECT 
'{{ vpc_name }}' as vpc_name,
selfLink as vpc_link
FROM google.compute.networks
WHERE name = '{{ vpc_name }}'
AND project = '{{ project }}'
```

## Query options

Query options are used with query anchors to provide options for the execution of the query.

### `retries` and `retry_delay`

The `retries` and `retry_delay` query options are typically used for asynchronous or long running provider operations.  This will allow the resource time to become available or reach the desired state without failing the stack.

```sql
/*+ postdeploy, retries=5, retry_delay=5 */
SELECT COUNT(*) as count FROM azure.resources.resource_groups
WHERE subscriptionId = '{{ subscription_id }}'
AND resourceGroupName = '{{ resource_group_name }}'
AND location = '{{ location }}'
AND JSON_EXTRACT(properties, '$.provisioningState') = 'Succeeded'
```

## Template filters

### `from_json`
`from_json` is a custom `stackql-deploy` filter which is used to convert a `json` string to a python dictionary or list.  The common use case is to take advantage of Jinja2 templating within `stackql-deploy` to dynamically generate SQL statements for infrastructure provisioning by converting JSON strings into Python dictionaries or lists, allowing for iteration and more flexible configuration management.

```sql  {2}
/*+ create */
{% for network_interface in network_interfaces | from_json %}
INSERT INTO google.compute.instances 
 (
  zone,
  project,
  data__name,
  data__machineType,
  data__canIpForward,
  data__deletionProtection,
  data__scheduling,
  data__networkInterfaces,
  data__disks,
  data__serviceAccounts,
  data__tags
 ) 
 SELECT
'{{ default_zone }}',
'{{ project }}',
'{{ instance_name_prefix }}-{{ loop.index }}',
'{{ machine_type }}',
true,
false,
'{{ scheduling }}',
'[ {{ network_interface | tojson }} ]',
'{{ disks }}',
'{{ service_accounts }}',
'{{ tags }}';
{% endfor %}
```

### `tojson`
`tojson` is a built-in Jinja2 filter to convert a Python dictionary or list into a `json` string.  This may be required if you have used the `from_json` filter as shown here:

```sql  {25}
/*+ create */
{% for network_interface in network_interfaces | from_json %}
INSERT INTO google.compute.instances 
 (
  zone,
  project,
  data__name,
  data__machineType,
  data__canIpForward,
  data__deletionProtection,
  data__scheduling,
  data__networkInterfaces,
  data__disks,
  data__serviceAccounts,
  data__tags
 ) 
 SELECT
'{{ default_zone }}',
'{{ project }}',
'{{ instance_name_prefix }}-{{ loop.index }}',
'{{ machine_type }}',
true,
false,
'{{ scheduling }}',
'[ {{ network_interface | tojson }} ]',
'{{ disks }}',
'{{ service_accounts }}',
'{{ tags }}';
{% endfor %}
```

### `generate_patch_document`

`generate_patch_document` is a custom `stackql-deploy` filter which generates a patch document for the given resource according to https://datatracker.ietf.org/doc/html/rfc6902, this is designed for the AWS Cloud Control API, which requires a patch document to update resources.  An example of this filter used to update the `NotificationConfiguration` for an existing AWS bucket is shown here:

```sql  {3-5}
/*+ createorupdate */
update aws.s3.buckets 
set data__PatchDocument = string('{{ {
    "NotificationConfiguration": transfer_notification_config
    } | generate_patch_document }}') 
WHERE 
region = '{{ region }}' 
AND data__Identifier = '{{ transfer_bucket_name }}';
```

### `base64_encode`

`base64_encode` is a custom `stackql-deploy` filter used to generate a `base64` encoded value for a given input string, this is often specified as an input requirement for a free text field in a resource.  This example shows how to `base64` encode the `UserData` field for an AWS EC2 instance:

```sql {13}
/*+ create */
INSERT INTO aws.ec2.instances (
 ImageId,
 InstanceType,
 SubnetId,
 UserData,
 region
)
SELECT 
 '{{ ami_id }}',
 '{{ instance_type }}',
 '{{ instance_subnet_id }}',
 '{{ user_data | base64_encode }}',
 '{{ region }}';
```

## Examples

### `resource` type example

This example is a `resource` file for a public IP address in a Google stack.

<File name='public_address.iql'>

```sql
/*+ preflight */
SELECT COUNT(*) as count FROM google.compute.addresses
WHERE name = '{{ address_name }}'
AND project = '{{ project }}'
AND region = '{{ region }}'

/*+ create */
INSERT INTO google.compute.addresses
(
 project,
 region,
 data__name
) 
SELECT
'{{ project }}',
'{{ region }}',
'{{ address_name }}'

/*+ postdeploy, retries=5, retry_delay=10 */
SELECT COUNT(*) as count FROM google.compute.addresses
WHERE name = '{{ address_name }}'
AND project = '{{ project }}'
AND region = '{{ region }}'

/*+ delete */
DELETE FROM google.compute.addresses
WHERE address = '{{ address_name }}' AND project = '{{ project }}'
AND region = '{{ region }}'

/*+ exports */
SELECT address
FROM google.compute.addresses
WHERE name = '{{ address_name }}'
AND project = '{{ project }}'
AND region = '{{ region }}'
```

</File>

### `query` type example

This `query` example demonstrates retrieving the KMS key id for a given key alias in AWS.

<File name='get_logging_kms_key_id.iql'>

```sql
/*+ exports, retries=5, retry_delay=5 */
SELECT
target_key_id as logging_kms_key_id
FROM aws.kms.aliases
WHERE region = '{{ region }}'
AND data__Identifier = 'alias/{{ stack_name }}/{{ stack_env }}/logging';
```

</File>