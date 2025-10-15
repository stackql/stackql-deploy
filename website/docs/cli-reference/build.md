---
title: build
hide_title: true
hide_table_of_contents: false
keywords:
  - stackql
  - stackql-deploy
  - infrastructure-as-code
  - configuration-as-data
tags:
  - stackql
  - stackql-deploy
  - infrastructure-as-code
  - configuration-as-data  
description: Documentation for the build command in StackQL Deploy
image: "/img/stackql-cover.png"
---

# <span className="docFieldHeading">`build`</span>

Command used to create or update resources in a StackQL environment.

* * * 

## Syntax

<code>stackql-deploy <span className="docFieldHeading">build</span> STACK_DIR STACK_ENV [FLAGS]</code>

* * *

## Arguments

| Argument | Description | Example |
|--|--|--|
|`STACK_DIR`|The directory containing the stack configuration files | `my-stack` |
|`STACK_ENV`|The target environment for the stack deployment | `dev` |  

:::info

`STACK_DIR` can be an absolute or relative path.  

`STACK_ENV` is a user defined environment symbol (e.g. `dev`, `sit`, `prd`) which is used to deploy your stack to different environments.

:::

## Optional Flags

| Flag | Description | Example |
|--|--|--|
|<span class="nowrap">`--log-level`</span>|Set the logging level. Default is `INFO` | `--log-level DEBUG` |
|<span class="nowrap">`--env-file`</span>|Specify an environment variables file. Default is `.env` | `--env-file .env` |
|<span class="nowrap">`-e`</span> <span class="nowrap">`--env`</span>|Set additional environment variables (can be used multiple times) | `--env DB_USER=admin` |
|<span class="nowrap">`--dry-run`</span>|Perform a dry run of the operation. No changes will be made | |
|<span class="nowrap">`--show-queries`</span>|Display the queries executed in the output logs | |
|<span class="nowrap">`--output-file`</span>|Export deployment variables to a JSON file after successful deployment | `--output-file ./outputs/deploy.json` |
|<span class="nowrap">`--download-dir`</span>|Custom download directory for StackQL | `/etc/stackql` |
|<span class="nowrap">`--custom-registry`</span>|Custom StackQL provider registry URL | `https://myreg` |

:::tip

Exported variables specified as `protected` in the respective resource definition in the `stackql_manifest.yml` file are obfuscated in the logs by default.

:::

* * *

## Examples

### Deploy a stack to a target environment

Deploy the stack defined in the `azure-stack` directory to the `sit` environment, setting additional environment variables to be used in the deployment:

```bash
stackql-deploy build azure-stack sit \
-e AZURE_SUBSCRIPTION_ID=631d1c6d-0000-0000-0000-688bfe4e1468
```

### Perform a dry run deployment

Perform a dry run or a stack defined in the `aws-stack` directory to a `prd` environment, showing templated queries without actually running them:

```bash
stackql-deploy build aws-stack prd \
--dry-run
```

### Specifying a custom environment file

Use a custom environment file `.env.prod` to supply environment variables to a stack defined in the `gcp-stack` directory to a `prod` environment:

```bash
stackql build gcp-stack prod \
--env-file .env.prod
```

### Export deployment variables to a file

Deploy a stack and export key deployment variables to a JSON file for use in CI/CD workflows or downstream processes:

```bash
stackql-deploy build databricks-stack prod \
--output-file ./outputs/deployment.json \
-e DATABRICKS_ACCOUNT_ID=12345678-1234-1234-1234-123456789012
```

This will create a JSON file containing the exported variables defined in the `exports` section of your `stackql_manifest.yml`:

```json
{
  "stack_name": "my-databricks-workspace",
  "stack_env": "prod",
  "workspace_name": "my-databricks-workspace-prod",
  "workspace_id": "123456789012345",
  "deployment_name": "dbc-ab123456-789a",
  "workspace_status": "RUNNING"
}
```

:::tip

`stack_name` and `stack_env` are automatically included in all exports and do not need to be listed in the manifest.

:::
