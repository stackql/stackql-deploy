# example `stackql-deploy` stack

Based upon the [__terraform-google-load-balanced-vms__](https://github.com/GoogleCloudPlatform/terraform-google-load-balanced-vms) project.

![load balanced vms](https://raw.githubusercontent.com/GoogleCloudPlatform/terraform-google-load-balanced-vms/c3e9669856df44a7b7399a7119eda3ae9ce5a2fa/assets/load_balanced_vms_v1.svg)

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
stackql-deploy init load-balanced-vms
```

this will create a directory named `load-balanced-vms` which can be updated for your stack, as you can see in this project.

## deploying using `stackql-deploy`

```bash
export GOOGLE_CREDENTIALS=$(cat ./testcreds/stackql-deploy-project-demo-service-account.json)
# deploy a stack
stackql-deploy build \
examples\google\load-balanced-vms \
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



stackql-deploy-project