# example `stackql-deploy` stack

Based upon the [Kubernetes the Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way) project.

## about `stackql-deploy`

[`stackql-deploy`](https://pypi.org/project/stackql-deploy/) is a multi cloud deployment automation and testing framework which is an alternative to Terraform or similar IaC tools.  `stackql-deploy` uses a declarative model/ELT based approach to cloud resource deployment (inspired by [`dbt`](https://www.getdbt.com/)).  Advantages of `stackql-deploy` include:

- declarative framework
- no state file (state is determined from the target environment)
- multi-cloud/omni-cloud ready
- includes resource tests which can include secure config tests

## instaling `stackql-deploy`

`stackql-deploy` is installed as a python based CLI using...

```bash
pip install stackql-deploy
# or
pip3 install stackql-deploy
```
> __Note for macOS users__  
> to install `stackql-deploy` in a virtual environment (which may be necessary on __macOS__), use the following:
> ```bash
> python3 -m venv myenv
> source myenv/bin/activate
> pip install stackql-deploy
> ```

## getting started with `stackql-deploy`

Once installed, use the `init` command to scaffold a sample project directory to get started:

```bash
stackql-deploy init k8s-the-hard-way
```

this will create a directory named `k8s-the-hard-way` which can be updated for your stack, as you can see in this project.

## deploying using `stackql-deploy`

```bash
export GOOGLE_CREDENTIALS=$(cat ./testcreds/k8s-the-hard-way-project-demo-service-account.json)
# deploy a stack
stackql-deploy build \
examples/google/k8s-the-hard-way \
dev \
-e GOOGLE_PROJECT=stackql-k8s-the-hard-way-demo \
--dry-run \
--log-level DEBUG

# test a stack
stackql-deploy test \
examples/google/k8s-the-hard-way \
dev \
-e GOOGLE_PROJECT=stackql-k8s-the-hard-way-demo \
--dry-run

# teardown a stack
stackql-deploy teardown \
examples/google/k8s-the-hard-way \
dev \
-e GOOGLE_PROJECT=stackql-k8s-the-hard-way-demo \
--dry-run
```
