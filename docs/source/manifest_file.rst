.. _manifest-file:

Understanding the Manifest File
===============================

The manifest file in **stackql-deploy** is used for defining and orchestrating the deployment of cloud resources. Modeled after successful data engineering practices, the manifest file allows you to declaratively specify what resources need to be provisioned, in what order, and with what configuration.

Structure of the Manifest File
------------------------------

The manifest file, named ``stackql_manifest.yml`` and located in the root of your project directory, is a YAML document which defines resources with properties and dependencies for your cloud/SaaS stack. Here's a breakdown of the key sections:

- **version**: Specifies the version of the manifest format. (*optional*)
- **name**: A unique name for the stack or project. (*optional - if not specified the project directory name is used*)
- **description**: A brief description of what the stack is for. (*optional*)
- **providers**: Lists the cloud providers and their configurations used in the stack.
- **globals**: Defines global variables that can be reused across the resource definitions.
- **resources**: Lists the cloud resources to be managed, along with their specific configurations and dependencies.

Here's an example of a simple manifest file:

.. code-block:: yaml

    version: 1
    name: activity_monitor
    description: OSS activity monitor stack
    providers:
      - azure
    globals:
      - name: subscription_id
        description: Azure subscription ID
        value: "{{ vars.AZURE_SUBSCRIPTION_ID }}"
      - name: location
        value: eastus
      - name: resource_group_name_base
        value: "activity-monitor"
    resources:
      - name: monitor_resource_group
        description: Azure resource group for activity monitor
        props:
          - name: resource_group_name
            description: Azure resource group name
            value: "{{ globals.resource_group_name_base }}-{{ globals.stack_env }}"

Using the Manifest File
-----------------------

**globals**:
Globals are variables defined at the top level of the manifest file and can be used across multiple resource definitions. They support dynamic values that can be interpolated at runtime using environment variables or other global values.

**resources**:
Each resource in the ``resources`` section represents a cloud resource that **stackql-deploy** will manage. The resource section includes:

- **name**: Identifier of the resource.
- **description**: What the resource represents.
- **props**: Properties or configurations specific to the resource. These can also include conditional logic or environment-specific values.

.. note::
   The ``stack_env`` is a special global variable for the user-specified environment label—e.g., ``prod``, ``

Conditional Logic and Environment-Specific Configurations
----------------------------------------------------------

You can define environment-specific configurations within the resource properties using nested `values` blocks keyed by the environment name. This allows you to tailor the deployment parameters according to the deployment environment (e.g., production, staging, development):

.. code-block:: yaml

    resources:
      - name: monitor_resource_group
        props:
          - name: resource_group_name
            values:
              prd:
                value: "activity-monitor-prd"
              dev:
                value: "activity-monitor-dev"

This configuration enables **stackql-deploy** to dynamically select the appropriate setting based on the `stack_env` provided during the deployment command.

Best Practices for Managing Manifest Files
------------------------------------------

- **Version Control**: Store your manifest files in a version control system to track changes and manage deployments across different stages of your development lifecycle.
- **Environment Separation**: Keep separate manifest files or sections for different environments to avoid conflicts and unintended deployments.
- **Security**: Be mindful of sensitive information in your manifest files. Use environment variables or secure vaults to manage credentials or sensitive configurations.

Summary
-------

The manifest file is a powerful tool in your **stackql-deploy** arsenal, allowing for precise and declarative infrastructure management. By understanding and utilizing the capabilities of the manifest file, you can significantly enhance the efficiency, repeatability, and maintainability of your cloud resource deployments.
