---
title: shell
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
description: Documentation for the shell command in StackQL Deploy
image: "/img/stackql-cover.png"
---

# <span className="docFieldHeading">`shell`</span>

Command used to launch the StackQL interactive shell.

* * *

## Syntax

<code>stackql-deploy <span className="docFieldHeading">shell</span> [FLAGS]</code>

* * *

## Optional Flags

| Flag | Description | Example |
|--|--|--|
|<span class="nowrap">`--download-dir`</span>|Custom download directory for StackQL | `/etc/stackql` |
|<span class="nowrap">`--custom-registry`</span>|Custom StackQL provider registry URL | `https://myreg` |

:::info

The `shell` command launches the interactive StackQL shell. If the `stackql` binary is not found in the provided paths, the command will fail with an error.

:::

* * *

## Examples

### Launch the StackQL shell using the default binary location

This command attempts to launch the StackQL shell using the binary location managed by the `pystackql` package:

```bash
stackql-deploy shell
```

### Launch the StackQL shell from a custom download directory

Specify a custom directory where the `stackql` binary is downloaded and run the StackQL shell:

```bash
stackql-deploy shell --download-dir /usr/local/bin/stackql
```

### Use a custom registry URL

Launch the StackQL shell using a custom StackQL provider registry:

```bash
stackql-deploy shell --custom-registry https://mycustomregistry.com
```
