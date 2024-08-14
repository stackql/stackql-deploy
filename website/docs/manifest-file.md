---
id: manifest-file
title: Maniftest File Structure
hide_title: true
hide_table_of_contents: false
description: A quick overview of how to get started with StackQL Deploy, including basic concepts and the essential components of a deployment.
tags: []
draft: false
unlisted: false
---

import File from '/src/components/File';

## Overview

The __`stackql_manifest.yml`__ file is in the root of a project (or stack) directory.  This `yaml` file defines all of the resources and their respective properties for all target deployment environments for your stack.  Resources are processed in the order in which they are declared in this file, resources can include `exports` which are variables used for subsequent resources in your stack (for example a `vpc_id` needed to deploy a `subnet`).  Global variables are configured here as well which can be sourced from external environment variables or secrets.

:::note

Secrets should not be saved in the __`stackql_manifest.yml`__ file, use `globals` and externally sourced variables (using the `-e` or `--env` options) at deploy time.

:::

## Fields

the fields within the __`stackql_manifest.yml`__ file are described in further detail here.

### `name`

- Type: `string`
- Required: __Yes__

The name of the stack, by default this is derived by the [__`init`__](/docs/cli-reference/init) command from the stack directory name (replacing `_` with `-` for resource and property name compliance).  This name can be overridden, the value for `name` is exposed as a global variable called `stack_name` which is often used with resource or property values so ensure that this string conforms to any naming restrictions.

<File name='stackql_manifest.yml'>

```yaml
name: kubernetes-the-hard-way
```

</File>

:::tip

Don't embed any environment symbols or designators in the `name` field, these are sourced at deploy time from the `STACK_ENV` argument to the `build`, `test` or `teardown` commands, and exposed for use in resource or property values as a global variable called `stack_env`.

:::

***

### `description`

- Type: `string`
- Required: __No__

Stack description, for documentation purposes only.

<File name='stackql_manifest.yml'>

```yaml
description: stackql-deploy example for kubernetes-the-hard-way
```

</File>

***

### `providers`

- Type: `string[]`
- Required: __Yes__

StackQL cloud or SaaS providers used in the stack.  These are pulled from the stackql provider regsitry if they are not present at deploy time.

<File name='stackql_manifest.yml'>

```yaml
providers:
  - google
```

</File>

***

### `globals`

- Type: `global[]`
- Required: __Yes__ (*can be an empty list if not required*)
- `global` Fields:
    - `name`: global variable name (*required*)
    - `value`: global variable value (*required*)
    - `description`: global variable description, for documentation purposes only

Global variables used throughout the stack, can be an empty list if not required.  Use the `{{ YOUR_ENV_VAR }}` notation in the `value` field of a `globals` list item to populate a global stack variable from an external environment variable or secret.

<File name='stackql_manifest.yml'>

```yaml
globals:
- name: project
  description: google project name
  value: "{{ GOOGLE_PROJECT }}"
- name: region
  value: australia-southeast1
- name: default_zone
  value: australia-southeast1-a
```

</File>

***

### `resources`

- Type: `resource[]`
- Required: __Yes__
- `resource` Fields:
    - `name`: global variable name (*required*)
    - `type`: resource type (*required* defaults to `resource`) (*detailed in [`resource.type`](#resourcetype)*)
    - `file`: resource query file for the resource, defaults to `resources/{name}.iql`
    - `props`: resource properties (*required*) (*detailed in [`resource.props`](#resourceprops)*) 
    - `exports`: resource exported variables (*detailed in [`resource.exports`](#resourceexports)*)
    - `protected`: resource protected exported variables (*detailed in [`resource.protected`](#resourceprotected)*)
    - `description`: resource description, for documentation purposes only

Defines resources in your stack, including the properties and their desired state values.

<File name='stackql_manifest.yml'>

```yaml
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
```

</File>

:::note

A file with the name of the resource with an `.iql` extension is expected to exist in the `resources` subdirectory of your stack directory.  You can reference a different file using the `file` field as shown here:

<File name='stackql_manifest.yml'>

```yaml
- name: controller_instances
  file: instances.iql
  props:
  - name: num_instances
    value: 3
  - name: instance_name_prefix
    value: "{{ stack_name }}-{{ stack_env }}-controller"
```

</File>

:::

***

### `resource.type`

- Type: `integer`
- Required: __No__

values include : `resource`, `query`, `script`

<File name='stackql_manifest.yml'>

```yaml
version: 1
```

</File>

***

### `resource.props`

- Type: `integer`
- Required: __No__

Document version.

<File name='stackql_manifest.yml'>

```yaml
version: 1
```

</File>

***

### `resource.exports`

- Type: `integer`
- Required: __No__

Document version.

<File name='stackql_manifest.yml'>

```yaml
version: 1
```

</File>

***

### `resource.protected`

- Type: `integer`
- Required: __No__

Document version.

<File name='stackql_manifest.yml'>

```yaml
version: 1
```

</File>

***

### `version`

- Type: `integer`
- Required: __No__

Document version.

<File name='stackql_manifest.yml'>

```yaml
version: 1
```

</File>


## Example `stackql_manifest.yml`

Here is a complete example of a `stackql_manifest.yml` file for a Google stack, for other examples see the [Template Library](/docs/template-library).

<File name='stackql_manifest.yml'>

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
  - name: fw_direction
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

</File>