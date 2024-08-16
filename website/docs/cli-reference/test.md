---
title: test
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
description: Documentation for the test command in StackQL Deploy
image: "/img/stackql-cover.png"
---

# <span className="docFieldHeading">`test`</span>

Command used to confirm the desired state of resources in a specified stack in a given environment.

* * *

## Syntax

<code>stackql-deploy <span className="docFieldHeading">test</span> STACK_DIR STACK_ENV [FLAGS]</code>

* * *

## Arguments

| Argument | Description | Example |
|--|--|--|
| `STACK_DIR` | The directory containing the stack configuration files | `my-stack` |
| `STACK_ENV` | The target environment for testing the stack | `dev` |

:::info

`STACK_DIR` can be an absolute or relative path.  

`STACK_ENV` is a user-defined environment symbol (e.g., `dev`, `sit`, `prd`) used to test your stack in different environments.

:::

## Optional Flags

| Flag | Description | Example |
|--|--|--|
| <span class="nowrap">`--log-level`</span> | Set the logging level. Default is `INFO` | `--log-level DEBUG` |
| <span class="nowrap">`--env-file`</span> | Specify an environment variables file. Default is `.env` | `--env-file .env` |
| <span class="nowrap">`-e`</span> <span class="nowrap">`--env`</span> | Set additional environment variables (can be used multiple times) | `--env DB_USER=admin` |
| <span class="nowrap">`--dry-run`</span> | Perform a dry run of the operation. No changes will be made | |
| <span class="nowrap">`--show-queries`</span> | Display the queries executed in the output logs | |
| <span class="nowrap">`--download-dir`</span>|Custom download directory for StackQL | `/etc/stackql` |
| <span class="nowrap">`--custom-registry`</span>|Custom StackQL provider registry URL | `https://myreg` |

:::tip

Exported variables specified as `protected` in the respective resource definition in the `stackql_manifest.yml` file are obfuscated in the logs by default.

:::

* * *

## Examples

### Confirm desired state for a stack in a target environment

Run tests for the stack defined in the `azure-stack` directory in the `sit` environment, setting additional environment variables:

```bash
stackql-deploy test azure-stack sit \
-e AZURE_SUBSCRIPTION_ID=631d1c6d-0000-0000-0000-688bfe4e1468
```

