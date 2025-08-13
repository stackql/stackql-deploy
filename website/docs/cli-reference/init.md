---
title: init
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
description: Documentation for the init command in StackQL Deploy
image: "/img/stackql-cover.png"
---

# <span className="docFieldHeading">`init`</span>

Command used to initialize a new `stackql-deploy` project structure.

* * *

## Syntax

<code>stackql-deploy <span className="docFieldHeading">init</span> STACK_DIR [FLAGS]</code>

* * *

## Arguments

| Argument | Description | Example |
|--|--|--|
| `STACK_DIR` | The directory (and name) for the project to be created | `my-stack` |

## Optional Flags

| Flag | Description | Example |
|--|--|--|
| <span class="nowrap">`--provider`</span> | Specify a cloud provider to start your project with. Supported values: `aws`, `azure`, `google`. Default is `azure`. | `--provider aws` |

* * *

## Description

The `init` command sets up a new project structure for a `stackql-deploy` stack. It creates the necessary directories and populates them with template files tailored to the specified cloud provider.

- If no provider is specified, the default provider is `azure`.
- The command ensures that the project name is converted to a lower-case, hyphen-separated format.
- The command also generates provider-specific example templates within the `resources` directory.

Supported providers include:

- **AWS**: Creates a sample VPC resource.
- **Azure**: Creates a sample Resource Group.
- **Google Cloud**: Creates a sample VPC resource.

If a provider is not supported, the command will default to `azure` and notify the user.

## Examples

### Initialize a new project with default provider

This command initializes a new project with the name `my-stack` using the default provider (`azure`):

```bash
stackql-deploy init my-stack
```
:::tip

`init` will create your project structure including the stack directory including the `stackql_manifest.yml` and `README.md` files, and a `resources` directory with a sample StackQL resource query file (`.iql` file). You can modify a project to use whichever providers are available in the [StackQL Provider Registry](https://stackql.io/providers).

:::

### Initialize a new project with the `aws` provider

Initialize a new project with the name `my-aws-stack` using `aws` as the provider:

```bash
stackql-deploy init my-aws-stack --provider aws
```
