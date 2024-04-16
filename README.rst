stackql-deploy
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

.. image:: images/stackql-deploy.png
   :alt: Workflow diagram

Installing from PyPI
--------------------

To install **stackql-deploy** directly from PyPI, run the following command:

.. code-block:: bash

    pip install stackql-deploy

This will install the latest version of **stackql-deploy** and its dependencies from the Python Package Index.

Running stackql-deploy
----------------------

Once installed, use the `deploy`, `test`, or `teardown` commands as shown here:

.. code-block:: bash

    stackql-deploy deploy prd example_stack -e AZURE_SUBSCRIPTION_ID 00000000-0000-0000-0000-000000000000 --dry-run
    stackql-deploy deploy prd example_stack -e AZURE_SUBSCRIPTION_ID 00000000-0000-0000-0000-000000000000
    stackql-deploy test prd example_stack -e AZURE_SUBSCRIPTION_ID 00000000-0000-0000-0000-000000000000
    stackql-deploy teardown prd example_stack -e AZURE_SUBSCRIPTION_ID 00000000-0000-0000-0000-000000000000

.. note::
   ``teardown`` deprovisions resources in reverse order to creation

additional options include:

- `--dry-run`: perform a dry run of the stack operations.
- `--on-failure=rollback`: action on failure: rollback, ignore or error.
- `--env-file=.env`: specify an environment variable file.
- `-e KEY=value`: pass additional environment variables.
- `--log-level` : logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL), defaults to INFO.

use `stackql-deploy info` to show information about the package and environment, for example

.. code-block:: none

    $ stackql-deploy info
    stackql-deploy version: 1.0.0
    pystackql version     : 3.5.4
    stackql version       : v0.5.612
    stackql binary path   : /mnt/c/LocalGitRepos/stackql/stackql-deploy/stackql
    platform              : Linux x86_64 (Linux-5.15.133.1-microsoft-standard-WSL2-x86_64-with-glibc2.35), Python 3.10.12

Use the `--help` option to see more information about the commands and options available:

.. code-block:: bash

    stackql-deploy --help

Project Structure
-----------------

**stackql-deploy** uses a modular structure where each component of the infrastructure is defined in separate files, allowing for clear separation of concerns and easy management. This example is based on a stack named ``example_stack``, with a resource named ``monitor_resource_group``.

::

    ├── example_stack
    │   ├── stackql_docs
    │   │   └── monitor_resource_group.md
    │   ├── stackql_manifest.yml
    │   ├── stackql_resources
    │   │   └── monitor_resource_group.iql
    │   └── stackql_tests
    │       └── monitor_resource_group.iql

Manifest File
-------------

- **Manifest File**: The ``stackql_manifest.yml`` is used to define your stack and manage dependencies between infrastructure components. This file defines which resources need to be provisioned before others and parameterizes resources based on environment variables or other configurations.

.. code-block:: yaml

    version: 1
    name: example_stack
    description: oss activity monitor stack
    providers:
      - azure
    globals:
      - name: subscription_id
        description: azure subscription id
        value: "{{ vars.AZURE_SUBSCRIPTION_ID }}"
      - name: location
        value: eastus
      - name: resource_group_name_base
        value: "activity-monitor"
    resources:
      - name: monitor_resource_group
        description: azure resource group for activity monitor
        props:
          - name: resource_group_name
            description: azure resource group name
            value: "{{ globals.resource_group_name_base }}-{{ globals.stack_env }}"
            # OR YOU CAN DO...
            # values:
            #   prd:
            #     value: "activity-monitor-prd"
            #   sit:
            #     value: "activity-monitor-sit"
            #   dev:
            #     value: "activity-monitor-dev"

Resource and Test SQL Files
----------------------------

These files define the SQL-like commands for creating, updating, and testing the deployment of resources.

**Resource SQL (stackql_resources/monitor_resource_group.iql):**

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

**Test SQL (stackql_tests/monitor_resource_group.iql):**

.. code-block:: sql

    /*+ preflight */
    SELECT COUNT(*) as count FROM azure.resources.resource_groups
    WHERE subscriptionId = '{{ subscription_id }}'
    AND resourceGroupName = '{{ resource_group_name }}'

    /*+ postdeploy, retries=5, retry_delay=5 */
    SELECT COUNT(*) as count FROM azure.resources.resource_groups
    WHERE subscriptionId = '{{ subscription_id }}'
    AND resourceGroupName = '{{ resource_group_name }}'
    AND location = '{{ location }}'
    AND JSON_EXTRACT(properties, '$.provisioningState') = 'Succeeded'

Building and Testing Locally
----------------------------

To get started with **stackql-deploy**, install it locally using pip:

.. code-block:: bash

    pip install -e .

Building and Deploying to PyPI
------------------------------

To distribute **stackql-deploy** on PyPI, you'll need to ensure that you have all required files set up correctly in your project directory. This typically includes your `setup.py`, `README.rst`, `LICENSE`, and any other necessary files.

Building the Package
^^^^^^^^^^^^^^^^^^^^

First, ensure you have the latest versions of `setuptools` and `wheel` installed:

.. code-block:: bash

    pip install --upgrade setuptools wheel

Then, navigate to your project root directory and build the distribution files:

.. code-block:: bash

    python setup.py sdist bdist_wheel

This command generates distribution packages in the `dist/` directory.

Uploading the Package to PyPI
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To upload the package to PyPI, you'll need to use `twine`, a utility for publishing Python packages. First, install `twine`:

.. code-block:: bash

    pip install twine

Then, use `twine` to upload all of the archives under `dist/`:

.. code-block:: bash

    twine upload dist/*

Building the Docs
^^^^^^^^^^^^^^^^^
Navigate to your `docs` directory and build the Sphinx documentation:

.. code-block:: bash

    cd docs
    make html

**stackql-deploy** simplifies cloud resource management by treating infrastructure as flexible, dynamically assessed code.

.. _stackql: https://github.com/stackql/stackql