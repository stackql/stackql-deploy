.. image:: https://stackql.io/img/stackql-logo-bold.png
    :alt: "stackql logo"
    :target: https://github.com/stackql/stackql
    :align: center

==========================================================================
Model driven resource provisioning and deployment framework using StackQL.
==========================================================================

.. .. image:: https://readthedocs.org/projects/pystackql/badge/?version=latest
..    :target: https://pystackql.readthedocs.io/en/latest/
..    :alt: Documentation Status

.. image:: https://img.shields.io/pypi/v/stackql-deploy
   :target: https://pypi.org/project/stackql-deploy/
   :alt: PyPI

==============

**stackql-deploy** is a multi-cloud Infrastructure as Code (IaC) framework using `stackql`_, inspired by dbt (data build tool), which manages data transformation workflows in analytics engineering by treating SQL scripts as models that can be built, tested, and materialized incrementally. You can create a similar framework for infrastructure provisioning with StackQL. The goal is to treat infrastructure-as-code (IaC) queries as models that can be deployed, managed, and interconnected.

This ELT/model-based framework to IaC allows you to provision, test, update and teardown multi-cloud stacks similar to how dbt manages data transformation projects, with the benefits of version control, peer review, and automation. This approach enables you to deploy complex, dependent infrastructure components in a reliable and repeatable manner.

The use of StackQL simplifies the interaction with cloud resources by using SQL-like syntax, making it easier to define and execute complex cloud management operations. Resources are provisioned with ``INSERT`` statements and tests are structured around ``SELECT`` statements.

Features include:

- Dynamic state determination (eliminating the need for state files)
- Simple flow control with rollback capabilities
- Single code base for multiple target environments
- SQL-based definitions for resources and tests

How stackql-deploy Works
------------------------

**stackql-deploy** orchestrates cloud resource provisioning by parsing SQL-like definitions. It determines the necessity of creating or updating resources based on preflight checks, and ensures the creation and correct desired configuration through post-deployment verifications.

.. image:: https://stackql.io/img/blog/stackql-deploy.png
    :alt: "stackql-deploy"
    :target: https://github.com/stackql/stackql

Installing from PyPI
--------------------

To install **stackql-deploy** directly from PyPI, run the following command:

.. code-block:: none

    pip install stackql-deploy

This will install the latest version of **stackql-deploy** and its dependencies from the Python Package Index.

Running stackql-deploy
----------------------

Once installed, use the `build`, `test`, or `teardown` commands as shown here:

.. code-block:: none

    stackql-deploy build prd example_stack -e AZURE_SUBSCRIPTION_ID 00000000-0000-0000-0000-000000000000 --dry-run
    stackql-deploy build prd example_stack -e AZURE_SUBSCRIPTION_ID 00000000-0000-0000-0000-000000000000
    stackql-deploy test prd example_stack -e AZURE_SUBSCRIPTION_ID 00000000-0000-0000-0000-000000000000
    stackql-deploy teardown prd example_stack -e AZURE_SUBSCRIPTION_ID 00000000-0000-0000-0000-000000000000

.. note::
   ``teardown`` deprovisions resources in reverse order to creation

additional options include:

- ``--dry-run``: perform a dry run of the stack operations.
- ``--on-failure=rollback``: action on failure: rollback, ignore or error.
- ``--env-file=.env``: specify an environment variable file.
- ``-e KEY=value```: pass additional environment variables.
- ``--log-level`` : logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL), defaults to INFO.

use ``stackql-deploy info`` to show information about the package and environment, for example

.. code-block:: none

    $ stackql-deploy info
    stackql-deploy version: 1.0.0
    pystackql version     : 3.5.4
    stackql version       : v0.5.612
    stackql binary path   : /mnt/c/LocalGitRepos/stackql/stackql-deploy/stackql
    platform              : Linux x86_64 (Linux-5.15.133.1-microsoft-standard-WSL2-x86_64-with-glibc2.35), Python 3.10.12

Use the ``--help`` option to see more information about the commands and options available:

.. code-block:: none

    stackql-deploy --help

Project Structure
-----------------

**stackql-deploy** uses a modular structure where each component of the infrastructure is defined in separate files, allowing for clear separation of concerns and easy management. This example is based on a stack named ``example_stack``, with a resource named ``monitor_resource_group``.

::

    ├── example_stack
    │   ├── stackql_manifest.yml
    │   └── resources
    │       └── monitor_resource_group.iql

.. note::
   use the ``init`` command to create a new project structure with sample files, for example ``stackql-deploy init example_stack``

Manifest File
-------------

- **Manifest File**: The ``stackql_manifest.yml`` is used to define your stack and manage dependencies between infrastructure components. This file defines which resources need to be provisioned before others and parameterizes resources based on environment variables or other configurations.

- **Providers**: List the cloud service providers that your stack will interact with. Each provider specified in the list will be initialized and made ready for use with the stack.

  .. code-block:: yaml

    providers:
      - azure
      - github

- **Globals**: Defines a set of global variables that can be used across the entire stack configuration. These variables can hold values related to environment settings, default configurations, or any commonly used data.

  .. code-block:: yaml

    globals:
      - name: subscription_id
        description: azure subscription id
        value: "{{ vars.AZURE_SUBSCRIPTION_ID }}"
      - name: location
        value: eastus
      ... (additional globals)

- **Resources**: Describes all the infrastructure components, such as networks, compute instances, databases, etc., that make up your stack. Here you can define the resources, their properties, and any dependencies between them.

  .. code-block:: yaml

    resources:
      - name: resource_group
        description: azure resource group for activity monitor app
      - name: storage_account
        description: azure storage account for activity monitor app
        ... (additional properties and exports)
      ...

  Each resource can have the following attributes:

  - **Name**: A unique identifier for the resource within the stack.
  - **Description**: A brief explanation of the resource's purpose and functionality.
  - **Type**: (Optional) Specifies the kind of resource (e.g., 'resource', 'query', 'script').
  - **Props**: (Optional) Lists the properties of the resource that define its configuration.
  - **Exports**: (Optional) Variables that are exported by this resource which can be used by other resources.
  - **Protected**: (Optional) A list of sensitive information that should not be logged or exposed outside secure contexts.

- **Scripts**: If your stack involves the execution of scripts for setup, data manipulation, or deployment actions, they are defined under the resources with a type of 'script'.

  .. code-block:: yaml

    - name: install_dependencies
      type: script
      run: |
        pip install pynacl
    ...

  The script's execution output can be captured and used within the stack or for further processing.

- **Integration with External Systems**: For stacks that interact with external services like GitHub, special resource types like 'query' can be used to fetch data from these services and use it within your deployment.

  .. code-block:: yaml

    - name: get_github_public_key
      type: query
      ... (additional properties and exports)

  This can be useful for dynamic configurations based on external state or metadata.

Resource and Test SQL Files
----------------------------

These files define the SQL-like commands for creating, updating, and testing the deployment of resources.

.. note:: 
   The SQL files use special **anchors** to indicate operations such as create, update, delete for resources, 
   and preflight or post-deployment checks for queries. For detailed explanations of these anchors, refer to the 
   `Resource SQL Anchors`_ and `Query SQL Anchors`_ sections.

**Resource SQL (resources/monitor_resource_group.iql):**

.. code-block:: sql

    /*+ create */
    INSERT INTO azure.resources.resource_groups(
      resourceGroupName,
      subscriptionId,
      data__location
    )
    SELECT
      '{{ resource_group_name }}',
      '{{ subscription_id }}',
      '{{ location }}'

    /*+ update */
    UPDATE azure.resources.resource_groups
    SET data__location = '{{ location }}'
    WHERE resourceGroupName = '{{ resource_group_name }}'
      AND subscriptionId = '{{ subscription_id }}'

    /*+ delete */
    DELETE FROM azure.resources.resource_groups
    WHERE resourceGroupName = '{{ resource_group_name }}' AND subscriptionId = '{{ subscription_id }}'

**Test SQL (resources/monitor_resource_group.iql):**

.. code-block:: sql

    /*+ preflight */
    SELECT COUNT(*) as count FROM azure.storage.accounts
    WHERE SPLIT_PART(SPLIT_PART(JSON_EXTRACT(properties, '$.primaryEndpoints.blob'), '//', 2), '.', 1) = '{{ storage_account_name }}'
    AND subscriptionId = '{{ subscription_id }}'
    AND resourceGroupName = '{{ resource_group_name }}'

    /*+ postdeploy, retries=5, retry_delay=5 */
    SELECT 
    COUNT(*) as count
    FROM azure.storage.accounts
    WHERE SPLIT_PART(SPLIT_PART(JSON_EXTRACT(properties, '$.primaryEndpoints.blob'), '//', 2), '.', 1) = '{{ storage_account_name }}'
    AND subscriptionId = '{{ subscription_id }}'
    AND resourceGroupName = '{{ resource_group_name }}'
    AND kind = '{{ storage_kind }}'
    AND JSON_EXTRACT(sku, '$.name') = 'Standard_LRS'
    AND JSON_EXTRACT(sku, '$.tier') = 'Standard'

    /*+ exports, retries=5, retry_delay=5 */
    select json_extract(keys, '$[0].value') as storage_account_key 
    from azure.storage.accounts_keys 
    WHERE resourceGroupName = '{{ resource_group_name }}' 
    AND subscriptionId = '{{ subscription_id }}' 
    AND accountName = '{{ storage_account_name }}'


Resource SQL Anchors
--------------------

Resource SQL files use special anchor comments as directives for the ``stackql-deploy`` tool to indicate the intended operations:

- **/*+ create */**
  This anchor precedes SQL ``INSERT`` statements for creating new resources.

  .. code-block:: sql

      /*+ create */
      INSERT INTO azure.resources.resource_groups(
        resourceGroupName,
        subscriptionId,
        data__location
      )
      SELECT
        '{{ resource_group_name }}',
        '{{ subscription_id }}',
        '{{ location }}'

- **/*+ createorupdate */**
  Specifies an operation to either create a new resource or update an existing one.

- **/*+ update */**
  Marks SQL ``UPDATE`` statements intended to modify existing resources.

- **/*+ delete */**
  Tags SQL ``DELETE`` statements for removing resources from the environment.

Query SQL Anchors
-----------------

Query SQL files contain SQL statements for testing and validation with the following anchors:

- **/*+ preflight */**
  Used to perform initial checks before a deployment.

  .. code-block:: sql

      /*+ preflight */
      SELECT COUNT(*) as count FROM azure.resources.resource_groups
      WHERE subscriptionId = '{{ subscription_id }}'
      AND resourceGroupName = '{{ resource_group_name }}'

- **/*+ postdeploy, retries=5, retry_delay=5 */**
  Post-deployment checks to confirm the success of the operation, with optional ``retries`` and ``retry_delay`` parameters.

  .. code-block:: sql

      /*+ postdeploy, retries=5, retry_delay=5 */
      SELECT COUNT(*) as count FROM azure.resources.resource_groups
      WHERE subscriptionId = '{{ subscription_id }}'
      AND resourceGroupName = '{{ resource_group_name }}'
      AND location = '{{ location }}'
      AND JSON_EXTRACT(properties, '$.provisioningState') = 'Succeeded'

- **/*+ exports, retries=5, retry_delay=5 */**
  Extracts and exports information after a deployment. Similar to post-deploy checks but specifically for exporting data.


.. note::
   The following parameters are used to control the behavior of retry mechanisms in SQL operations:

   - **``retries``** (optional, integer): Defines the number of times a query should be retried upon failure.
   - **``retry_delay``** (optional, integer): Sets the delay in seconds between each retry attempt.


**stackql-deploy** simplifies cloud resource management by treating infrastructure as flexible, dynamically assessed code.

.. _stackql: https://github.com/stackql/stackql
