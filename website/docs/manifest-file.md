---
id: manifest-file
title: Maniftest File
hide_title: false
hide_table_of_contents: false
description: A quick overview of how to get started with StackQL Deploy, including basic concepts and the essential components of a deployment.
tags: []
draft: false
unlisted: false
---

import * as ManifestFields from './manifest_fields';
import File from '/src/components/File';
export const headingColor = '#FF6347';

## Overview

The __`stackql_manifest.yml`__ file is in the root of a project (or stack) directory.  This `yaml` file defines all of the resources and their respective properties for all target deployment environments for your stack.  Resources are processed in the order in which they are declared in this file, resources can include `exports` which are variables used for subsequent resources in your stack (for example a `vpc_id` needed to deploy a `subnet`).  Global variables are configured here as well which can be sourced from external environment variables or secrets.

:::note

Secrets should not be saved in the __`stackql_manifest.yml`__ file, use `globals` and externally sourced variables (using the `-e` or `--env` options) at deploy time.

:::

## Fields

the fields within the __`stackql_manifest.yml`__ file are described in further detail here.

### <span className="docFieldHeading">`name`</span>

<ManifestFields.Name />

***

### <span className="docFieldHeading">`description`</span>

<ManifestFields.Description />

***

### <span className="docFieldHeading">`providers`</span>

<ManifestFields.Providers />

***

### <span className="docFieldHeading">`globals`</span>

<ManifestFields.Globals />

***

### <span className="docFieldHeading">`global.name`</span>

<ManifestFields.GlobalName />

***

### <span className="docFieldHeading">`global.value`</span>

<ManifestFields.GlobalValue />

***

### <span className="docFieldHeading">`global.description`</span>

<ManifestFields.GlobalDescription />

***

### <span className="docFieldHeading">`resources`</span>

<ManifestFields.Resources />

***

### <span className="docFieldHeading">`resource.name`</span>

<ManifestFields.ResourceName />

***

### <span className="docFieldHeading">`resource.type`</span>

<ManifestFields.ResourceType />

***

### <span className="docFieldHeading">`resource.file`</span>

<ManifestFields.ResourceFile />

***

### <span className="docFieldHeading">`resource.description`</span>

<ManifestFields.ResourceDescription />

***

### <span className="docFieldHeading">`resource.auth`</span>

<ManifestFields.ResourceAuth />

***

### <span className="docFieldHeading">`resource.exports`</span>

<ManifestFields.ResourceExports />

***

### <span className="docFieldHeading">`resource.protected`</span>

<ManifestFields.ResourceProtected />

***

### <span className="docFieldHeading">`resource.if`</span>

<ManifestFields.ResourceIf />

***

### <span className="docFieldHeading">`resource.props`</span>

<ManifestFields.ResourceProps />

***

### <span className="docFieldHeading">`resource.prop.name`</span>

<ManifestFields.ResourcePropName />

***

### <span className="docFieldHeading">`resource.prop.description`</span>

<ManifestFields.ResourcePropDescription />

***

### <span className="docFieldHeading">`resource.prop.value`</span>

<ManifestFields.ResourcePropValue />

***

### <span className="docFieldHeading">`resource.prop.values`</span>

<ManifestFields.ResourcePropValues />

***

### <span className="docFieldHeading">`resource.prop.merge`</span>

<ManifestFields.ResourcePropMerge />

***

### <span className="docFieldHeading">`version`</span>

<ManifestFields.Version />

***

## Example manifest file

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
