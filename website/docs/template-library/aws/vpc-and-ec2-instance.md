---
id: vpc-and-ec2-instance
title: AWS VPC and EC2 Instance
hide_title: false
hide_table_of_contents: false
description: A quick overview of how to get started with StackQL Deploy, including basic concepts and the essential components of a deployment.
tags: []
draft: false
unlisted: false
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

In this example, we'll demonstrate how to set up a simple VPC with an EC2 instance in AWS using `stackql-deploy`. This setup is ideal for getting started with basic networking and compute resources on AWS.

<div style={{ display: 'flex', justifyContent: 'center' }}>
  <img src="/img/library/aws/simple-aws-vpc-ec2-stack.png" alt="Simple AWS VPC EC2 Stack" style={{ width: '60%', height: 'auto' }} />
</div>
The EC2 instance is bootstrapped with a web server that serves a simple page using the EC2 instance `UserData` property.

## Deploying the Stack

> install `stackql-deploy` using `pip install stackql-deploy` (see [__Installing stackql-deploy__](/getting-started#installing-stackql-deploy)), set the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables, that's it!

Once you have setup your project directory (your "stack"), you can use the `stackql-deploy` cli application to deploy, test or teardown the stack in any given environment.  To deploy the stack to an environment labeled `sit`, run the following:

```bash
stackql-deploy build aws-stack sit \
-e AWS_REGION=ap-southeast-2
```
Use the `--dry-run` flag to view the queries to be run without actually running them, heres an example of a `dry-run` operation for a `prd` environment:

```bash
stackql-deploy build aws-stack prd \
-e AWS_REGION=ap-southeast-2 \
--dry-run
```

## stackql_manifest.yml

The `stackql_manifest.yml` defines the resources in yoru stack and their property values (for one or more environments).

<details>
  <summary>Click to expand the <code>stackql_manifest.yml</code> file</summary>

```yaml
version: 1
name: "aws-stack"
description: description for "aws-stack"
providers:
  - aws
globals:
  - name: region
    description: aws region
    value: "{{ AWS_REGION }}"
  - name: global_tags
    value:
      - Key: Provisioner
        Value: stackql
      - Key: StackName
        Value: "{{ stack_name }}"
      - Key: StackEnv
        Value: "{{ stack_env }}"
resources:
  - name: example_vpc
    props:
      - name: vpc_cidr_block
        values:
          prd:
            value: "10.0.0.0/16"
          sit:
            value: "10.1.0.0/16"
          dev:
            value: "10.2.0.0/16"
      - name: vpc_tags
        value:
          - Key: Name
            Value: "{{ stack_name }}-{{ stack_env }}-vpc"
        merge: 
          - global_tags
    exports:
      - vpc_id
      - vpc_cidr_block
  - name: example_subnet
    props:
      - name: subnet_cidr_block
        values:
          prd:
            value: "10.0.1.0/24"
          sit:
            value: "10.1.1.0/24"
          dev:
            value: "10.2.1.0/24"
      - name: subnet_tags
        value:
          - Key: Name
            Value: "{{ stack_name }}-{{ stack_env }}-subnet"
        merge: ['global_tags']      
    exports:
      - subnet_id
      - availability_zone
  - name: example_inet_gateway
    props:
      - name: inet_gateway_tags
        value:
          - Key: Name
            Value: "{{ stack_name }}-{{ stack_env }}-inet-gateway"
        merge: ['global_tags']
    exports:
      - internet_gateway_id
  - name: example_inet_gw_attachment
    props: []
  - name: example_route_table
    props:
      - name: route_table_tags
        value:
          - Key: Name
            Value: "{{ stack_name }}-{{ stack_env }}-route-table"
        merge: ['global_tags']
    exports:
      - route_table_id
  - name: example_subnet_rt_assn
    props: []
    exports:
      - route_table_assn_id
  - name: example_inet_route
    props: []
    exports:
      - inet_route_indentifer
  - name: example_security_group
    props:
      - name: group_description
        value: "web security group for {{ stack_name }} ({{ stack_env }} environment)"
      - name: group_name
        value: "{{ stack_name }}-{{ stack_env }}-web-sg"
      - name: sg_tags
        value:
          - Key: Name
            Value: "{{ stack_name }}-{{ stack_env }}-web-sg"
        merge: ['global_tags']
      - name: security_group_ingress
        value:
          - CidrIp: "0.0.0.0/0"
            Description: Allow HTTP traffic
            FromPort: 80
            ToPort: 80
            IpProtocol: "tcp"
          - CidrIp: "{{ vpc_cidr_block }}"
            Description: Allow SSH traffic from the internal network
            FromPort: 22
            ToPort: 22
            IpProtocol: "tcp"
      - name: security_group_egress
        value:
          - CidrIp: "0.0.0.0/0"
            Description: Allow all outbound traffic
            FromPort: 0
            ToPort: 0
            IpProtocol: "-1"
    exports:
      - security_group_id            
  - name: example_web_server
    props:
      - name: instance_name
        value: "{{ stack_name }}-{{ stack_env }}-instance"
      - name: ami_id
        value: ami-030a5acd7c996ef60
      - name: instance_type
        value: t2.micro
      - name: instance_subnet_id
        value: "{{ subnet_id }}"
      - name: sg_ids
        value:
          - "{{ security_group_id }}"
      - name: user_data
        value: |
          #!/bin/bash
          yum update -y
          yum install -y httpd
          systemctl start httpd
          systemctl enable httpd
          echo '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>StackQL on AWS</title><style>body {font-family: Tahoma, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f0f0f0; text-align: center;} img {height: auto;} code {background-color: #e8e8e8; padding: 2px 6px; border-radius: 3px; font-weight: bold;} p {font-size: 1.5em; font-weight: bold;}</style></head>' > /var/www/html/index.html
          echo '<body><div><a href="https://github.com/stackql/stackql"><img src="https://stackql.io/img/stackql-logo-bold.png" alt="StackQL Logo"></a><p>Hello, <a href="https://pypi.org/project/stackql-deploy/"><code>stackql-deploy</code></a> on AWS!</p></div></body></html>' >> /var/www/html/index.html
      - name: instance_tags
        value:
          - Key: Name
            Value: "{{ stack_name }}-{{ stack_env }}-instance"
        merge: ['global_tags']
    exports:
      - instance_id
      - public_dns_name
```

</details>

## Resource Query Files

Resource query files are templates which are used to create, update, test and delete resources in your stack.  Here are some example resource query files in this example:

<Tabs
  defaultValue="vpc"
  values={[
    { label: 'example_vpc.iql', value: 'vpc', },
    { label: 'example_subnet.iql', value: 'subnet', },
  ]}
>
<TabItem value="vpc">

```sql
/*+ exists */
SELECT COUNT(*) as count FROM
(
SELECT vpc_id,
json_group_object(tag_key, tag_value) as tags
FROM aws.ec2.vpc_tags
WHERE region = '{{ region }}'
AND cidr_block = '{{ vpc_cidr_block }}'
GROUP BY vpc_id
HAVING json_extract(tags, '$.Provisioner') = 'stackql'
AND json_extract(tags, '$.StackName') = '{{ stack_name }}'
AND json_extract(tags, '$.StackEnv') = '{{ stack_env }}'
) t; 

/*+ create */
INSERT INTO aws.ec2.vpcs (
 CidrBlock,
 Tags,
 EnableDnsSupport,
 EnableDnsHostnames, 
 region
)
SELECT 
 '{{ vpc_cidr_block }}',
 '{{ vpc_tags }}',
 true,
 true,
 '{{ region }}';

/*+ statecheck, retries=5, retry_delay=5 */
SELECT COUNT(*) as count FROM
(
SELECT vpc_id,
cidr_block,
json_group_object(tag_key, tag_value) as tags
FROM aws.ec2.vpc_tags
WHERE region = '{{ region }}'
AND cidr_block = '{{ vpc_cidr_block }}'
GROUP BY vpc_id
HAVING json_extract(tags, '$.Provisioner') = 'stackql'
AND json_extract(tags, '$.StackName') = '{{ stack_name }}'
AND json_extract(tags, '$.StackEnv') = '{{ stack_env }}'
) t
WHERE cidr_block = '{{ vpc_cidr_block

 }}'; 

/*+ exports */
SELECT vpc_id, vpc_cidr_block FROM
(
SELECT vpc_id, cidr_block as "vpc_cidr_block",
json_group_object(tag_key, tag_value) as tags
FROM aws.ec2.vpc_tags
WHERE region = '{{ region }}'
AND cidr_block = '{{ vpc_cidr_block }}'
GROUP BY vpc_id
HAVING json_extract(tags, '$.Provisioner') = 'stackql'
AND json_extract(tags, '$.StackName') = '{{ stack_name }}'
AND json_extract(tags, '$.StackEnv') = '{{ stack_env }}'
) t;

/*+ delete */
DELETE FROM aws.ec2.vpcs
WHERE data__Identifier = '{{ vpc_id }}'
AND region = '{{ region }}';
```

</TabItem>
<TabItem value="subnet">

```sql
/*+ exists */
SELECT COUNT(*) as count FROM
(
SELECT subnet_id,
json_group_object(tag_key, tag_value) as tags
FROM aws.ec2.subnet_tags
WHERE region = '{{ region }}'
AND vpc_id = '{{ vpc_id }}'
GROUP BY subnet_id
HAVING json_extract(tags, '$.Provisioner') = 'stackql'
AND json_extract(tags, '$.StackName') = '{{ stack_name }}'
AND json_extract(tags, '$.StackEnv') = '{{ stack_env }}'
) t; 

/*+ create */
INSERT INTO aws.ec2.subnets (
 VpcId,
 CidrBlock,
 MapPublicIpOnLaunch,
 Tags,
 region
)
SELECT 
 '{{ vpc_id }}',
 '{{ subnet_cidr_block }}',
 true,
 '{{ subnet_tags }}',
 '{{ region }}';

/*+ statecheck, retries=5, retry_delay=5 */
SELECT COUNT(*) as count FROM
(
SELECT subnet_id,
cidr_block,
json_group_object(tag_key, tag_value) as tags
FROM aws.ec2.subnet_tags
WHERE region = '{{ region }}'
AND vpc_id = '{{ vpc_id }}'
GROUP BY subnet_id
HAVING json_extract(tags, '$.Provisioner') = 'stackql'
AND json_extract(tags, '$.StackName') = '{{ stack_name }}'
AND json_extract(tags, '$.StackEnv') = '{{ stack_env }}'
) t
WHERE cidr_block = '{{ subnet_cidr_block }}'; 

/*+ exports */
SELECT subnet_id, availability_zone FROM
(
SELECT subnet_id, 
availability_zone,
cidr_block,
json_group_object(tag_key, tag_value) as tags
FROM aws.ec2.subnet_tags
WHERE region = '{{ region }}'
AND vpc_id = '{{ vpc_id }}'
GROUP BY subnet_id
HAVING json_extract(tags, '$.Provisioner') = 'stackql'
AND json_extract(tags, '$.StackName') = '{{ stack_name }}'
AND json_extract(tags, '$.StackEnv') = '{{ stack_env }}'
) t
WHERE cidr_block = '{{ subnet_cidr_block }}'; 

/*+ delete */
DELETE FROM aws.ec2.subnets
WHERE data__Identifier = '{{ subnet_id }}'
AND region = '{{ region }}';
```

</TabItem>
</Tabs>

## More Information

The complete code for this example stack is available [__here__](https://github.com/stackql/stackql-deploy/tree/main/examples/aws/aws-stack). For more information on how to use StackQL and StackQL Deploy, visit:

- [`aws` provider docs](https://stackql.io/providers/aws)
- [`stackql`](https://github.com/stackql)
- [`stackql-deploy` PyPI home page](https://pypi.org/project/stackql-deploy/)
- [`stackql-deploy` GitHub repo](https://github.com/stackql/stackql-deploy)
