---
id: k8s-the-hard-way
title: K8s the Hard Way
hide_title: false
hide_table_of_contents: false
description: A step-by-step guide to setting up Kubernetes the Hard Way using StackQL Deploy, based on the popular project by Kelsey Hightower.
tags: [kubernetes, stackql, google cloud, devops, infrastructure, IaC]
draft: false
unlisted: false
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

This guide is based on the [Kubernetes the Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way) project by Kelsey Hightower, adapted to be deployed using `stackql-deploy`.

## About `stackql-deploy`

[`stackql-deploy`](https://pypi.org/project/stackql-deploy/) is a multi-cloud deployment automation and testing framework that serves as an alternative to Terraform and other IaC tools. Inspired by [`dbt`](https://www.getdbt.com/), `stackql-deploy` offers several advantages:

- Declarative framework
- No state file (state is determined from the target environment)
- Multi-cloud/omni-cloud ready
- Includes resource tests, which can include secure configuration tests

## Installing `stackql-deploy`

To install `stackql-deploy`, use the following command:

```bash
pip install stackql-deploy
```
for more information on installing `stackql-deploy` see [__Installing stackql-deploy__](/getting-started#installing-stackql-deploy).

## Deploying Using `stackql-deploy`

Here’s an example of deploying, testing, and tearing down this example stack:

```bash
export GOOGLE_CREDENTIALS=$(cat ./creds.json)

# Deploy a stack in the prd environment
stackql-deploy build \
k8s-the-hard-way \
prd \
-e GOOGLE_PROJECT=stackql-k8s-the-hard-way-demo \
--dry-run \
--log-level DEBUG

# Test a stack in the sit environment
stackql-deploy test \
examples/k8s-the-hard-way \
sit \
-e GOOGLE_PROJECT=stackql-k8s-the-hard-way-demo \
--dry-run

# Teardown a stack in the dev environment
stackql-deploy teardown \
k8s-the-hard-way \
dev \
-e GOOGLE_PROJECT=stackql-k8s-the-hard-way-demo \
--dry-run
```

## stackql_manifest.yml

The `stackql_manifest.yml` file defines the resources in your stack and their property values (for one or more environments).

<details>
  <summary>Click to expand the <code>stackql_manifest.yml</code> file</summary>

```yaml
version: 1
name: kubernetes-the-hard-way
description: stackql-deploy example for kubernetes-the-hard-way
providers:
  - google
globals:
  - name: project
    description: google project name
    value: "{{ GOOGLE_PROJECT }}"
  - name: region
    value: australia-southeast1
  - name: default_zone
    value: australia-southeast1-a
resources:
  - name: network
    description: vpc network for k8s-the-hard-way sample app
    props:
      - name: vpc_name
        description: name for the vpc
        value: "{{ stack_name }}-{{ stack_env }}-vpc"
    exports:
      - vpc_name    
      - vpc_link    
  - name: subnetwork
    props:
      - name: subnet_name
        value: "{{ stack_name }}-{{ stack_env }}-{{ region }}-subnet"  
      - name: ip_cidr_range
        values:
          prd:
            value: 192.168.0.0/16
          sit:
            value: 10.10.0.0/16
          dev:
            value: 10.240.0.0/24
    exports:
      - subnet_name    
      - subnet_link            
  - name: public_address
    props:
      - name: address_name
        value: "{{ stack_name }}-{{ stack_env }}-{{ region }}-ip-addr"  
    exports:
      - address    
  - name: controller_instances
    file: instances.iql
    props:
      - name: num_instances
        value: 3
      - name: instance_name_prefix
        value: "{{ stack_name }}-{{ stack_env }}-controller"
      - name: disks
        value:
          - autoDelete: true
            boot: true
            initializeParams:
              diskSizeGb: 10
              sourceImage: https://compute.googleapis.com/compute/v1/projects/ubuntu-os-cloud/global/images/family/ubuntu-2004-lts
            mode: READ_WRITE
            type: PERSISTENT
      - name: machine_type
        value: "https://compute.googleapis.com/compute/v1/projects/{{ project }}/zones/{{ default_zone }}/machineTypes/f1-micro"          
      - name: scheduling
        value: {automaticRestart: true}
      - name: tags
        value: {items: ["{{ stack_name }}", "controller"]}
      - name: service_accounts
        value:
          - email: default
            scopes:
              - https://www.googleapis.com/auth/compute
              - https://www.googleapis.com/auth/devstorage.read_only
              - https://www.googleapis.com/auth/logging.write
              - https://www.googleapis.com/auth/monitoring
              - https://www.googleapis.com/auth/service.management.readonly
              - https://www.googleapis.com/auth/servicecontrol
      - name: network_interfaces
        values:
          dev:
            value: 
              - {networkIP: "10.240.0.10", subnetwork: "{{ subnet_link }}", accessConfigs: [{name: external-nat, type: ONE_TO_ONE_NAT}]}              
              - {networkIP: "10.240.0.11", subnetwork: "{{ subnet_link }}", accessConfigs: [{name: external-nat, type: ONE_TO_ONE_NAT}]}              
              - {networkIP: "10.240.0.12", subnetwork: "{{ subnet_link }}", accessConfigs: [{name: external-nat, type: ONE_TO_ONE_NAT}]}              
  - name: worker_instances
    file: instances.iql
    props:
      - name: num_instances
        value: 3
      - name: instance_name_prefix
        value: "{{ stack_name }}-{{ stack_env }}-worker"
      - name: disks
        value:
          - autoDelete: true
            boot: true
            initializeParams:
              diskSizeGb: 10
              sourceImage: https://compute.googleapis.com/compute/v1/projects/ubuntu-os-cloud/global/images/family/ubuntu-2004-lts
            mode: READ_WRITE
            type: PERSISTENT
      - name: machine_type
        value: "https://compute.googleapis.com/compute/v1/projects/{{ project }}/zones/{{ default_zone }}/machineTypes/f1-micro"          
      - name: scheduling
        value: {automaticRestart: true}
      - name: tags
        value: {items: ["{{ stack_name }}", "worker"]}
      - name: service_accounts
        value:
          - email: default
            scopes:
              - https://www.googleapis.com/auth/compute
              - https://www.googleapis.com/auth/devstorage.read_only
              - https://www.googleapis.com/auth/logging.write
              - https://www.googleapis.com/auth/monitoring
              - https://www.googleapis.com/auth/service.management.readonly
              - https://www.googleapis.com/auth/servicecontrol
      - name: network_interfaces
        values:
          dev:
            value: 
              - {networkIP: "10.240.0.20", subnetwork: "{{ subnet_link }}", accessConfigs: [{name: external-nat, type: ONE_TO_ONE_NAT}]}              
              - {networkIP: "10.240.0.21", subnetwork: "{{ subnet_link }}", accessConfigs: [{name: external-nat, type: ONE_TO_ONE_NAT}]}              
              - {networkIP: "10.240.0.22", subnetwork: "{{ subnet_link }}", accessConfigs: [{name: external-nat, type: ONE_TO_ONE_NAT}]} 
  - name: health_checks
    props:
      - name: health_check_name
        value: kubernetes
      - name: health_check_interval_sec
        value: 5
      - name: health_check_description
        value: Kubernetes Health Check
      - name: health_check_timeout_sec
        value: 5
      - name: health_check_healthy_threshold
        value: 2
      - name: health_check_unhealthy_threshold
        value: 2
      - name: health_check_host
        value: kubernetes.default.svc.cluster.local
      - name: health_check_port
        value: 80
      - name: health_check_path
        value: /healthz
    exports:
      - health_check_link
  - name: internal_firewall
    file: firewalls.iql
    props:
      - name: fw_name
        value: "{{ stack_name }}-{{ stack_env }}-allow-internal-fw"
      -

 name: fw_direction
        value: INGRESS
      - name: fw_source_ranges
        values:
          dev:
            value: ["10.240.0.0/24", "10.200.0.0/16"]
      - name: fw_allowed
        value: [{IPProtocol: tcp}, {IPProtocol: udp}, {IPProtocol: icmp}]
  - name: external_firewall
    file: firewalls.iql
    props:
      - name: fw_name
        value: "{{ stack_name }}-{{ stack_env }}-allow-external-fw"
      - name: fw_direction
        value: INGRESS
      - name: fw_source_ranges
        values:
          dev:
            value: ["0.0.0.0/0"]
      - name: fw_allowed
        value: [{IPProtocol: tcp, ports: ["22"]}, {IPProtocol: tcp, ports: ["6443"]},{IPProtocol: icmp}]
  - name: health_check_firewall
    file: firewalls.iql
    props:
      - name: fw_name
        value: "{{ stack_name }}-{{ stack_env }}-allow-health-check-fw"
      - name: fw_direction
        value: INGRESS
      - name: fw_source_ranges
        values:
          dev:
            value: ["209.85.152.0/22", "209.85.204.0/22", "35.191.0.0/16"]
      - name: fw_allowed
        value: [{IPProtocol: tcp}]
  - name: get_controller_instances
    type: query
    exports:
      - controller_instances
  - name: target_pool
    props:
      - name: target_pool_name
        value: "{{ stack_name }}-{{ stack_env }}-target-pool"
      - name: target_pool_session_affinity
        value: NONE
      - name: target_pool_health_checks
        value: ["{{ health_check_link }}"]
      - name: target_pool_instances
        value: "{{ controller_instances }}"
    exports:
      - target_pool_link
  - name: forwarding_rule
    props:
      - name: forwarding_rule_name
        value: "{{ stack_name }}-{{ stack_env }}-forwarding-rule"
      - name: forwarding_rule_load_balancing_scheme
        value: EXTERNAL
      - name: forwarding_rule_port_range
        value: 6443
  - name: routes
    props:
      - name: num_routes
        value: 3
      - name: route_name_prefix
        value: "{{ stack_name }}-{{ stack_env }}-route"
      - name: route_priority
        value: 1000
      - name: route_data
        values:
          dev:
            value: 
              - {dest_range: "10.200.0.0/24", next_hop_ip: "10.240.0.20"}              
              - {dest_range: "10.200.1.0/24", next_hop_ip: "10.240.0.21"}              
              - {dest_range: "10.200.2.0/24", next_hop_ip: "10.240.0.22"}              
```

</details>

## Resource Query Files

Here are some example resource query files used to create, update, test, and delete resources in this stack:

<Tabs
  defaultValue="network"
  values={[
    { label: 'network.iql', value: 'network', },
    { label: 'firewalls.iql', value: 'firewalls', },
  ]}
>
<TabItem value="network">

```sql
/*+ exists */
SELECT COUNT(*) as count FROM google.compute.networks
WHERE name = '{{ vpc_name }}'
AND project = '{{ project }}'

/*+ create */
INSERT INTO google.compute.networks
(
 project,
 data__name,
 data__autoCreateSubnetworks,
 data__routingConfig
) 
SELECT
'{{ project }}',
'{{ vpc_name }}',
false,
'{"routingMode": "REGIONAL"}'

/*+ update */
UPDATE google.compute.networks
SET data__autoCreateSubnetworks = false
AND data__routingConfig = '{"routingMode": "REGIONAL"}'
WHERE network = '{{ vpc_name }}' AND project = '{{ project }}'

/*+ statecheck, retries=5, retry_delay=10 */
SELECT COUNT(*) as count FROM google.compute.networks
WHERE name = '{{ vpc_name }}'
AND project = '{{ project }}'
AND autoCreateSubnetworks = false
AND JSON_EXTRACT(routingConfig, '$.routingMode') = 'REGIONAL'

/*+ delete, retries=20, retry_delay=10 */
DELETE FROM google.compute.networks
WHERE network = '{{ vpc_name }}' AND project = '{{ project }}'

/*+ exports */
SELECT 
'{{ vpc_name }}' as vpc_name,
selfLink as vpc_link
FROM google.compute.networks
WHERE name = '{{ vpc_name }}'
AND project = '{{ project }}'
```

</TabItem>
<TabItem value="firewalls">

```sql
/*+ exists */
SELECT COUNT(*) as count FROM google.compute.firewalls
WHERE project = '{{ project }}'
AND name = '{{ fw_name }}'

/*+ create */
INSERT INTO google.compute.firewalls
(
 project,
 data__name,
 data__network,
 data__direction,
 data__sourceRanges,
 data__allowed
) 
SELECT
 '{{ project }}',
 '{{ fw_name}}',
 '{{ vpc_link }}',
 '{{ fw_direction }}',
 '{{ fw_source_ranges }}',
 '{{ fw_allowed }}'

/*+ statecheck, retries=5, retry_delay=10 */
SELECT COUNT(*) as count FROM
(
SELECT
network = '{{ vpc_link }}' as test_network,
direction = '{{ fw_direction }}' as test_direction,
JSON_EQUAL(allowed, '{{ fw_allowed }}') as test_allowed,
JSON_EQUAL(sourceRanges, '{{ fw_source_ranges }}') as test_source_ranges
FROM google.compute.firewalls
WHERE project = '{{ project }}'
AND name = '{{ fw_name }}'
) t
WHERE test_network = 1
AND test_direction = 1
AND test_allowed = 1
AND test_source_ranges = 1;

/*+ update */
UPDATE google.compute.firewalls
SET
 data__network = '{{ vpc_link }}',
 data__direction = '{{ fw_direction }}',
 data__sourceRanges = '{{ fw_source_ranges }}',
 data__allowed = '{{ fw_allowed }}'
WHERE firewall = '{{ fw_name}}'
AND project = '{{ project }}'

/*+ delete, retries=20, retry_delay=10 */
DELETE FROM google.compute.firewalls
WHERE project = '{{ project }}'
AND firewall = '{{ fw_name }}'
```

</TabItem>
</Tabs>

## More Information

The complete code for this example stack is available [__here__](https://github.com/stackql/stackql-deploy/tree/main/examples/k8s-the-hard-way). For more information on how to use StackQL and StackQL Deploy, visit:

- [`google` provider docs](https://stackql.io/providers/google)
- [`stackql`](https://github.com/stackql)
- [`stackql-deploy` PyPI home page](https://pypi.org/project/stackql-deploy/)
- [`stackql-deploy` GitHub repo](https://github.com/stackql/stackql-deploy)
