# `stackql-deploy` starter project for `azure`

```bash
stackql-deploy test \
examples/databricks/all-purpose-cluster prd \
-e AWS_REGION=ap-southeast-2 \
-e DATABRICKS_ACCOUNT_ID=ebfcc5a9-9d49-4c93-b651-b3ee6cf1c9ce
```

```bash
stackql-deploy build \
examples/databricks/all-purpose-cluster prd \
-e AWS_REGION=ap-southeast-2 \
-e DATABRICKS_ACCOUNT_ID=ebfcc5a9-9d49-4c93-b651-b3ee6cf1c9ce
```