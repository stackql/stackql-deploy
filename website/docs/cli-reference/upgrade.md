---
title: upgrade
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
description: Documentation for the upgrade command in StackQL Deploy
image: "/img/stackql-cover.png"
---

# <span className="docFieldHeading">`upgrade`</span>

Command used to upgrade the `pystackql` package and `stackql` binary to the latest versions.

* * *

## Syntax

<code>stackql-deploy <span className="docFieldHeading">upgrade</span></code>

* * *

## Description

The `upgrade` command automates the process of upgrading both the `pystackql` package and the `stackql` binary to their latest available versions. This ensures that your environment is up-to-date with the latest features, improvements, and security patches.

When the `upgrade` command is run, it first attempts to upgrade the `pystackql` package using `pip`. After that, it upgrades the `stackql` binary to the latest version.

## Examples

### Upgrade `pystackql` and `stackql` to the latest versions

This command will upgrade both the `pystackql` package and the `stackql` binary:

```bash
stackql-deploy upgrade
```

outputs...

```plaintext
upgrading pystackql package...
pystackql package upgraded successfully.
pystackql package upgraded from 3.6.4 to 3.7.0.
upgrading stackql binary, current version v0.5.708...
stackql binary upgraded to v0.6.002.
```

If the `pystackql` package or the `stackql` binary is already up-to-date, the command will notify you accordingly.
