---
id: simple-vnet-and-vm
title: VNet and Virtual Machine
hide_title: false
hide_table_of_contents: false
description: A quick overview of how to get started with StackQL Deploy, including basic concepts and the essential components of a deployment on Azure.
tags: []
draft: false
unlisted: false
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

In this example, we'll demonstrate how to set up a simple Virtual Network (VNet) with a Virtual Machine (VM) in Azure using `stackql-deploy`. This setup is ideal for getting started with basic networking and compute resources on Azure.

<div style={{ display: 'flex', justifyContent: 'center' }}>
  <img src="/img/library/azure/azure_vnet_and_vm.png" alt="Simple Azure VNet VM Stack" style={{ width: '60%', height: 'auto' }} />
</div>

The Virtual Machine is bootstrapped with a web server that serves a simple page using the Azure Custom Script Extension.

## Deploying the Stack

> Install `stackql-deploy` using `pip install stackql` (see [__Installing stackql-deploy__](/getting-started#installing-stackql-deploy)), set the `AZURE_SUBSCRIPTION_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, and `AZURE_TENANT_ID` environment variables, and you're ready to go!

Once you have set up your project directory (your "stack"), you can use the `stackql-deploy` CLI application to deploy, test, or teardown the stack in any given environment. To deploy the stack to an environment labeled `sit`, run the following:

```bash
stackql-deploy build azure-stack sit \
-e AZURE_SUBSCRIPTION_ID=$AZURE_SUBSCRIPTION_ID
```

Use the `--dry-run` flag to view the queries to be run without actually running them. Here’s an example of a `dry-run` operation for a `prd` environment:

```bash
stackql-deploy build azure-stack prd \
-e AZURE_SUBSCRIPTION_ID=$AZURE_SUBSCRIPTION_ID \
--dry-run
```

## stackql_manifest.yml

The `stackql_manifest.yml` defines the resources in your stack and their property values (for one or more environments).

<details>
  <summary>Click to expand the <code>stackql_manifest.yml</code> file</summary>

```yaml
version: 1
name: "azure-stack"
description: description for "azure-stack"
providers:
  - azure
globals:
  - name: subscription_id
    description: azure subscription id
    value: "{{ AZURE_SUBSCRIPTION_ID }}"
  - name: location
    description: default location for resources
    value: eastus
  - name: global_tags
    value:
      provisioner: stackql
      stackName: "{{ stack_name }}"
      stackEnv: "{{ stack_env }}"
resources:
  - name: example_resource_group
    props:
      - name: resource_group_name
        value: "{{ stack_name }}-{{ stack_env }}-rg"
    exports:
      - resource_group_name        
  - name: example_vnet
    props:
      - name: vnet_name
        value: "{{ stack_name }}-{{ stack_env }}-vnet"    
      - name: vnet_cidr_block
        values:
          prd:
            value: "10.0.0.0/16"
          sit:
            value: "10.1.0.0/16"
          dev:
            value: "10.2.0.0/16"
    exports:
      - vnet_name
      - vnet_cidr_block
  - name: example_subnet
    props:
      - name: subnet_name
        value: "{{ stack_name }}-{{ stack_env }}-subnet-1"    
      - name: subnet_cidr
        values:
          prd:
            value: "10.0.1.0/24"
          sit:
            value: "10.1.1.0/24"
          dev:
            value: "10.2.1.0/24"
    exports:
      - subnet_name
      - subnet_id
  - name: example_public_ip
    props:
      - name: public_ip_name
        value: "{{ stack_name }}-{{ stack_env }}-public-ip"
    exports:
      - public_ip_name
      - public_ip_id
      - public_ip_address
  - name: example_nsg
    props:
      - name: nsg_name
        value: "{{ stack_name }}-{{ stack_env }}-nsg"
      - name: security_rules
        value:
          - name: AllowHTTP
            properties:
              access: Allow
              protocol: Tcp
              direction: Inbound
              priority: 100
              sourceAddressPrefix: "*"
              sourcePortRange: "*"
              destinationAddressPrefix: "*"
              destinationPortRange: "8080"
          - name: AllowSSH
            properties:
              access: Allow
              protocol: Tcp
              direction: Inbound
              priority: 200
              sourceAddressPrefix: "{{ vnet_cidr_block }}"
              sourcePortRange: "*"
              destinationAddressPrefix: "*"
              destinationPortRange: "22"
    exports:
      - network_security_group_id
  - name: example_nic
    props:
      - name: nic_name
        value: "{{ stack_name }}-{{ stack_env }}-nic"
      - name: nic_ip_config
        value:
          name: ipconfig1
          properties:
            subnet:
              id: "{{ subnet_id }}"
            privateIPAllocationMethod: Dynamic
            publicIPAddress:
              id: "{{ public_ip_id }}"
    exports:
      - network_interface_id
  - name: example_web_server
    props:
      - name: vm_name
        value: "{{ stack_name }}-{{ stack_env }}-vm"
      - name: hardwareProfile
        value:
          vmSize: Standard_DS1_v2
      - name: storageProfile
        value:
          imageReference:
            publisher: Canonical
            offer: UbuntuServer
            sku: 18.04-LTS
            version: latest
          osDisk:
            name: "{{ stack_name }}-{{ stack_env }}-vm-disk1"
            createOption: FromImage
            managedDisk: 
              storageAccountType: Standard_LRS
            diskSizeGB: 30
      - name: osProfile
        value:
          computerName: myVM-{{ stack_name }}-{{ stack_env }}
          adminUsername: azureuser
          adminPassword: Password1234!
          linuxConfiguration:
            disablePasswordAuthentication: false
      - name: networkProfile
        value:
          networkInterfaces:
            - id: "{{ network_interface_id }}"
    exports:
      - vm_name
      - vm_id
  - name: example_vm_ext
    props:
      - name: vm_ext_name
        value: "{{ stack_name }}-{{ stack_env }}-microsoft.custom-script-linux"
      - name: command_to_execute
        value: |
          wget -O index.html https://raw.githubusercontent.com/stackql/stackql-deploy/main/examples/azure/azure-stack/resources/hello-stackql.html && nohup busybox httpd -f -p 8080 &
    exports:
      - web_url
```

</details>

## Resource Query Files

Resource query files are templates used to create, update, test, and delete resources in your stack. Here are some example resource query files for this Azure example:

<Tabs
  defaultValue="vnet"
  values={[
    { label: 'example_vnet.iql', value: 'vnet', },
    { label: 'example_subnet.iql', value: 'subnet', },
  ]}
>
<TabItem value="vnet">

```sql
/*+ createorupdate */
INSERT INTO azure.network.virtual_networks(
   virtualNetworkName,
   resourceGroupName, 
   subscriptionId, 
   data__location,
   data__properties,
   data__tags   
)
SELECT
   '{{ vnet_name }}',
   '{{ resource_group_name }}',
   '{{ subscription_id }}',
   '{{ location }}',
   '{"addressSpace": {"addressPrefixes":["{{ vnet_cidr_block }}"]}}',
   '{{ global_tags }}'

/*+ statecheck, retries=5, retry_delay=5 */
SELECT COUNT(*) as count FROM azure.network.virtual_networks
WHERE subscriptionId = '{{ subscription_id }}'
AND resourceGroupName = '{{ resource_group_name }}'
AND virtualNetworkName = '{{ vnet_name }}'
AND JSON_EXTRACT(properties, '$.addressSpace.addressPrefixes[0]') = '{{ vnet_cidr_block }}'

/*+ exports */
SELECT '{{ vnet_name }}' as vnet_name,
'{{ vnet_cidr_block }}' as vnet_cidr_block

/*+ delete */
DELETE FROM azure.network.virtual_networks
WHERE subscriptionId = '{{ subscription_id }}'
AND resourceGroupName = '{{ resource_group_name }}'
AND virtualNetworkName = '{{ vnet_name }}'
```

</TabItem>
<TabItem value="subnet">

```sql
/*+ createorupdate */
INSERT INTO azure.network.subnets(
   subnetName,
   virtualNetworkName,
   resourceGroupName, 
   subscriptionId, 
   data__properties
)
SELECT
   '{{ subnet_name }}',
   '{{ vnet_name }}',
   '{{ resource_group_name }}',
   '{{ subscription_id }}',
   '{"addressPrefix": "{{ subnet_cidr }}"}'

/*+ statecheck, retries=5, retry_delay=5 */
SELECT COUNT(*) as count FROM azure.network.subnets
WHERE subscriptionId = '{{ subscription_id }}'
AND resourceGroupName = '{{ resource_group_name }}'
AND virtualNetworkName = '{{ vnet_name }}'
AND subnetName = '{{ subnet_name }}'
AND JSON_EXTRACT(properties, '$.addressPrefix') = '{{ subnet_cidr }}'

/*+ exports */
SELECT '{{ subnet_name }}' as subnet_name,
id as subnet_id
FROM azure.network.subnets
WHERE subscriptionId = '{{ subscription_id }}'
AND resourceGroupName = '{{ resource_group_name }}'
AND virtualNetworkName = '{{ vnet_name }}'
AND subnetName = '{{ subnet_name }}'

/*+ delete */
DELETE FROM azure.network.subnets
WHERE subscriptionId = '{{ subscription_id }}'
AND resourceGroupName = '{{ resource_group_name }}'
AND virtualNetworkName = '{{ vnet_name }}'
AND subnetName = '{{ subnet_name }}'
```

</TabItem>
</Tabs>

## More Information

The complete code for this example stack is available [__here__](https://github.com/stackql/stackql-deploy/tree/main/examples/azure/azure-stack). For more information on how to use StackQL and StackQL Deploy, visit:

- [`azure` provider docs](https://stackql.io/providers/azure)
- [`stackql`](https://github.com/stackql)
- [`stackql-deploy` PyPI home page](https://pypi.org/project/stackql-deploy/)
- [`stackql-deploy` GitHub repo](https://github.com/stackql/stackql-deploy)
