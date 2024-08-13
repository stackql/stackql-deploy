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

# <code>build</code>

Command used to create or update resources in a StackQL environment.

* * * 

## Syntax

`stackql-deploy build STACK_DIR STACK_ENV [FLAGS]`

* * *

## Arguments

| Argument | Description | Example |
|--|--|--|
|`STACK_DIR`|The directory containing the stack configuration files | `my-stack` |
|`STACK_ENV`|The target environment for the stack deployment | `dev` |  

## Flags

| Flag | Description | Example |
|--|--|--|
|<span class="nowrap">`--log-level`</span>|Set the logging level. Default is `INFO` | `--log-level DEBUG` |
|<span class="nowrap">`--env-file`</span>|Specify an environment variables file. Default is `.env` | `--env-file .env` |
|<span class="nowrap">`-e`</span> <span class="nowrap">`--env`</span>|Set additional environment variables (can be used multiple times) | `--env DB_USER=admin` |
|<span class="nowrap">`--dry-run`</span>|Perform a dry run of the operation. No changes will be made | |
|<span class="nowrap">`--show-queries`</span>|Display the queries executed in the output logs | |

* * *

## Examples

### Deploy a Stack to a Target Environment

Deploy the stack defined in the `azure-stack` directory to the `sit` environment, setting additional environment variables to be used in the deployment:

```bash
stackql-deploy build azure-stack sit \
-e AZURE_SUBSCRIPTION_ID=631d1c6d-0000-0000-0000-688bfe4e1468
```

### Perform a Dry Run Deployment

Perform a dry run or a stack defined in the `aws-stack` directory to a `prd` environment, showing templated queries without actually running them:

```bash
stackql-deploy build aws-stack prd \
--dry-run
```

### Specifying a Custom Environment File

Use a custom environment file `.env.prod` to supply environment variables to a stack defined in the `gcp-stack` directory to a `prod` environment:

```bash
stackql build gcp-stack prod \
--env-file .env.prod
```
