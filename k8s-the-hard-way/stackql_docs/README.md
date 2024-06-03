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
```

## getting started with `stackql-deploy`

Once installed, use the `init` command to scaffold a sample project directory to get started:

```bash
stackql-deploy init k8s-the-hard-way
```

this will create a directory named `k8s-the-hard-way` which can be updated for your stack, as you can see in this project.

## deploying using `stackql-deploy`

```bash
export GOOGLE_CREDENTIALS=$(cat ./creds.json)
stackql-deploy build k8s-the-hard-way dev --env GOOGLE_PROJECT=stackql-k8s-the-hard-way-demo --dry-run
stackql-deploy build k8s-the-hard-way dev --env GOOGLE_PROJECT=stackql-k8s-the-hard-way-demo
stackql-deploy test k8s-the-hard-way dev --env GOOGLE_PROJECT=stackql-k8s-the-hard-way-demo --dry-run
stackql-deploy test k8s-the-hard-way dev --env GOOGLE_PROJECT=stackql-k8s-the-hard-way-demo
stackql-deploy teardown k8s-the-hard-way dev --env GOOGLE_PROJECT=stackql-k8s-the-hard-way-demo --dry-run
stackql-deploy teardown k8s-the-hard-way dev --env GOOGLE_PROJECT=stackql-k8s-the-hard-way-demo
```


SELECT COUNT(*) as count FROM google.compute.subnetworks
WHERE name = 'kubernetes-the-hard-way-dev-australia-southeast1-subnet'
AND project = 'stackql-k8s-the-hard-way-demo'
AND region = 'australia-southeast1'


SELECT COUNT(*) as count FROM google.compute.subnetworks
WHERE subnetwork = 'kubernetes-the-hard-way-dev-australia-southeast1-subnet'
AND project = 'stackql-k8s-the-hard-way-demo'
AND region = 'australia-southeast1';


v24.06.00234


SELECT COUNT(*) as count FROM google.compute.subnetworks
WHERE name = 'kubernetes-the-hard-way-dev-australia-southeast1-subnet'
AND project = 'stackql-k8s-the-hard-way-demo'
AND region = 'australia-southeast1';


AND network = 'https://compute.googleapis.com/compute/v1/projects/stackql-k8s-the-hard-way-demo/global/networks/kubernetes-the-hard-way-dev-vpc';