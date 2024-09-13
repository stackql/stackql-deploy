# `stackql-deploy` starter project for `azure`

> for starter projects using other providers, try `stackql-deploy my_stack --provider=aws` or `stackql-deploy my_stack --provider=google`

see the following links for more information on `stackql`, `stackql-deploy` and the `azure` provider:

- [`azure` provider docs](https://stackql.io/registry/azure)
- [`stackql`](https://github.com/stackql/stackql)
- [`stackql-deploy` PyPI home page](https://pypi.org/project/stackql-deploy/)
- [`stackql-deploy` GitHub repo](https://github.com/stackql/stackql-deploy)

## Overview

__`stackql-deploy`__ is a stateless, declarative, SQL driven Infrastructure-as-Code (IaC) framework.  There is no state file required as the current state is assessed for each resource at runtime.  __`stackql-deploy`__ is capable of provisioning, deprovisioning and testing a stack which can include resources across different providers, like a stack spanning `azure` and `azure` for example.  

## Prerequisites

This example requires `stackql-deploy` to be installed using __`pip install stackql-deploy`__.  The host used to run `stackql-deploy` needs the necessary environment variables set to authenticate to your specific provider, in the case of the `azure` provider, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and optionally `AWS_SESSION_TOKEN` must be set, for more information on authentication to `azure` see the [`azure` provider documentation](https://azure.stackql.io/providers/azure).

> __Note for macOS users__  
> to install `stackql-deploy` in a virtual environment (which may be necessary on __macOS__), use the following:
> ```bash
> python3 -m venv myenv
> source myenv/bin/activate
> pip install stackql-deploy
> ```

## Usage

Adjust the values in the [__`stackql_manifest.yml`__](stackql_manifest.yml) file if desired.  The [__`stackql_manifest.yml`__](stackql_manifest.yml) file contains resource configuration variables to support multiple deployment environments, these will be used for `stackql` queries in the `resources` and `resources` folders.  

The syntax for the `stackql-deploy` command is as follows:

```bash
stackql-deploy { build | test | teardown } { stack-directory } { deployment environment} [ optional flags ]
``` 

### Deploying a stack

For example, to deploy the stack to an environment labeled `sit`, run the following:

```bash
export AZURE_VM_ADMIN_PASSWORD="Your_password_here1"
stackql-deploy build \
examples/azure/azure-stack sit \
-e AZURE_SUBSCRIPTION_ID=631d1c6d-2a65-43e7-93c2-688bfe4e1468 \
-e AZURE_VM_ADMIN_PASSWORD=$AZURE_VM_ADMIN_PASSWORD
```

Use the `--dry-run` flag to view the queries to be run without actually running them, for example:

```bash
stackql-deploy build \
examples/azure/azure-stack sit \
-e AZURE_SUBSCRIPTION_ID=631d1c6d-2a65-43e7-93c2-688bfe4e1468 \
--dry-run
```

### Testing a stack

To test a stack to ensure that all resources are present and in the desired state, run the following (in our `sit` deployment example):

```bash
stackql-deploy test \
examples/azure/azure-stack sit \
-e AZURE_SUBSCRIPTION_ID=631d1c6d-2a65-43e7-93c2-688bfe4e1468 \
-e AZURE_VM_ADMIN_PASSWORD=$AZURE_VM_ADMIN_PASSWORD
```

### Tearing down a stack

To destroy or deprovision all resources in a stack for our `sit` deployment example, run the following:

```bash
stackql-deploy teardown \
examples/azure/azure-stack sit \
-e AZURE_SUBSCRIPTION_ID=631d1c6d-2a65-43e7-93c2-688bfe4e1468 \
-e AZURE_VM_ADMIN_PASSWORD=$AZURE_VM_ADMIN_PASSWORD
```