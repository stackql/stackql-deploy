# `stackql-deploy` starter project for `snowflake`

> for starter projects using other providers, try `stackql-deploy examples/snowflake/entitlements --provider=aws` or `stackql-deploy examples/snowflake/entitlements --provider=google`

see the following links for more information on `stackql`, `stackql-deploy` and the `snowflake` provider:

- [`snowflake` provider docs](https://stackql.io/registry/snowflake)
- [`stackql`](https://github.com/stackql/stackql)
- [`stackql-deploy` PyPI home page](https://pypi.org/project/stackql-deploy/)
- [`stackql-deploy` GitHub repo](https://github.com/stackql/stackql-deploy)

## Overview

__`stackql-deploy`__ is a stateless, declarative, SQL driven Infrastructure-as-Code (IaC) framework.  There is no state file required as the current state is assessed for each resource at runtime.  __`stackql-deploy`__ is capable of provisioning, deprovisioning and testing a stack which can include resources across different providers, like a stack spanning `azure` and `aws` for example.  

## Prerequisites

This example requires `stackql-deploy` to be installed using __`pip install stackql-deploy`__.  The host used to run `stackql-deploy` needs the necessary environment variables set to authenticate to your specific provider, in the case of the `snowflake` provider, `SNOWFLAKE_PAT` must be set, for more information on authentication to `snowflake` see the [`snowflake` provider documentation](https://snowflake.stackql.io/providers/snowflake).

## Usage

Adjust the values in the [__`stackql_manifest.yml`__](stackql_manifest.yml) file if desired.  The [__`stackql_manifest.yml`__](stackql_manifest.yml) file contains resource configuration variables to support multiple deployment environments, these will be used for `stackql` queries in the `resources` folder.  

The syntax for the `stackql-deploy` command is as follows:

```bash
stackql-deploy { build | test | teardown } { stack-directory } { deployment environment} [ optional flags ]
``` 

### Deploying a stack

For example, to deploy the stack named examples/snowflake/entitlements to an environment labeled `sit`, run the following:

```bash
stackql-deploy build examples/snowflake/entitlements sit \
-e SNOWFLAKE_ORG=OKXVNMC  -e SNOWFLAKE_ACCOUNT=VH34026
```

Use the `--dry-run` flag to view the queries to be run without actually running them, for example:

```bash
stackql-deploy build examples/snowflake/entitlements sit \
-e SNOWFLAKE_ORG=OKXVNMC  -e SNOWFLAKE_ACCOUNT=VH34026 \
--dry-run
```

### Testing a stack

To test a stack to ensure that all resources are present and in the desired state, run the following (in our `sit` deployment example):

```bash
stackql-deploy test examples/snowflake/entitlements sit \
-e SNOWFLAKE_ORG=OKXVNMC  -e SNOWFLAKE_ACCOUNT=VH34026
```

### Tearing down a stack

To destroy or deprovision all resources in a stack for our `sit` deployment example, run the following:

```bash
stackql-deploy teardown examples/snowflake/entitlements sit \
-e SNOWFLAKE_ORG=OKXVNMC  -e SNOWFLAKE_ACCOUNT=VH34026
```