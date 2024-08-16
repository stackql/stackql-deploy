---
title: info
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
description: Documentation for the info command in StackQL Deploy
image: "/img/stackql-cover.png"
---

# <span className="docFieldHeading">`info`</span>

Command used to display version information and environment details for the StackQL Deploy program and its dependencies.

* * *

## Syntax

<code>stackql-deploy <span className="docFieldHeading">info</span> [FLAGS]</code>

* * *

## Optional Flags

| Flag | Description | Example |
|--|--|--|
| <span class="nowrap">`--download-dir`</span> | Custom download directory for StackQL | `/etc/stackql` |
| <span class="nowrap">`--custom-registry`</span> | Custom StackQL provider registry URL | `https://myreg` |

* * *

## Description

The `info` command provides detailed information about the StackQL Deploy environment, including the versions of `stackql-deploy`, `pystackql`, and the `stackql` binary, as well as the paths and platform information. If a custom provider registry is used, that information will also be displayed. Additionally, the command lists all installed providers and their versions.

## Examples

### Display version information

Display the version information of the `stackql-deploy` tool, its dependencies, and the installed providers:

```bash
stackql-deploy info
```
outputs...

```plaintext
stackql-deploy version: 1.6.1
pystackql version     : 3.6.4
stackql version       : v0.5.708
stackql binary path   : /home/javen/.local/stackql
platform              : Linux x86_64 (Linux-5.15.133.1-microsoft-standard-WSL2-x86_64-with-glibc2.35), Python 3.10.12

installed providers:  : 
aws                   : v24.07.00246
azure                 : v24.06.00242
google                : v24.06.00236
```

### Specify a custom `stackql` binary location

`stackql-deploy` will automatically download the `stackql` binary when a command is run, if the binary does not exist in the default directory.  Alternatively, you can supply the `--download-dir` flag to specify the location of an existing `stackql` binary, or have `stackql-deploy` download the `stackql` binary to this location.

```bash
stackql-deploy info \
--download-dir /usr/local/bin/stackql
```

### Specify a custom provider registry URL

By default the public [StackQL Provider Registry](https://github.com/stackql/stackql-provider-registry) is used for provider definitions, to supply custom providers or use an alternate registry, specify the custom regsitry URL using the `--custom-registry` flag.  The following example will use the public StackQL dev provider registry.

```bash
stackql-deploy info \
--custom-registry="https://registry-dev.stackql.app/providers"
```
