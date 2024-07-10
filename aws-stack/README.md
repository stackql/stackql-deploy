# `stackql-deploy` starter project for `aws`

> for starter projects using other providers, try `stackql-deploy my_stack --provider=azure` or `stackql-deploy my_stack --provider=google`

[`aws` provider docs](https://stackql.io/registry/aws)

[`stackql`](https://github.com/stackql/stackql)

[`stackql-deploy` PyPI home page](https://pypi.org/project/stackql-deploy/)

[`stackql-deploy` GitHub repo](https://github.com/stackql/stackql-deploy)


stackql-deploy build aws-stack sit \
-e AWS_REGION=ap-southeast-2 \
--dry-run

stackql-deploy build aws-stack sit \
--log-level DEBUG

stackql-deploy test aws-stack sit \
--log-level DEBUG