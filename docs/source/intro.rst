Welcome to stackql-deploy
=========================

**stackql-deploy** is an innovative command-line interface (CLI) tool designed to manage multi-cloud Infrastructure as Code (IaC) using a model akin to the Data Build Tool (dbt) which is prevalent in the field of analytics engineering. This tool leverages the powerful SQL-like query capabilities of StackQL, allowing you to manage and provision cloud infrastructure with unprecedented ease and clarity.

Why stackql-deploy?
-------------------

**stackql-deploy** transforms the way teams approach Infrastructure as Code. By treating IaC queries as models, this tool enables incremental, manageable, and scalable deployments, testing, and teardowns of cloud infrastructure across multiple environments. Here are a few reasons why **stackql-deploy** stands out:

- **Model-based Approach**: Inspired by dbt's successful model for data transformations, stackql-deploy applies similar principles to infrastructure management, enabling a structured, version-controlled, and testable approach to deploying cloud resources.

- **Unified Multi-Cloud Management**: With stackql-deploy, manage resources across different cloud providers using a single, unified interface. This eliminates the need to juggle multiple tools and APIs, simplifying the complexity traditionally associated with multi-cloud environments.

- **SQL-like Syntax**: StackQL’s native SQL-like syntax makes defining and managing cloud resources as simple as writing a SQL query. This reduces the learning curve for teams familiar with SQL and allows them to leverage existing skills and tools.

- **Dynamic State Management**: Unlike traditional IaC tools that require manual handling of state files, stackql-deploy dynamically determines the state of resources, ensuring deployments are always up-to-date with minimal overhead.

Getting Started
---------------

**stackql-deploy** is easy to install and configure, making it straightforward to integrate into your existing workflows. Whether you are managing a few cloud resources or orchestrating complex multi-cloud environments, starting with **stackql-deploy** is just a few steps away:

1. **Installation**: Install **stackql-deploy** directly from PyPI using pip:

   .. code-block:: bash

       pip install stackql-deploy

   This will install the latest version of **stackql-deploy** and its dependencies from the Python Package Index.

   .. note::

      **Note for macOS users**: If you encounter an `externally-managed-environment` error or prefer to avoid installing packages globally, it is recommended to use a virtual environment. To create and activate a virtual environment on macOS, run the following commands:

      .. code-block:: bash

          python3 -m venv myenv
          source myenv/bin/activate
          pip install stackql-deploy

2. **Quick Example**: Here’s a quick example to show how you can deploy a sample resource:

   .. code-block:: bash

       stackql-deploy build prod ./my_project --env-file .env

   This command will deploy resources defined in `./my_project` under the production environment, using environment variables specified in the `.env` file.

3. **Learn More**: Dive deeper into the capabilities of stackql-deploy by exploring the subsequent sections of this documentation, covering everything from detailed command usage to advanced configuration options.

4. **Getting Help**: To see all available commands and options, use the `--help` option:

   .. code-block:: bash

       stackql-deploy --help

5. **Diagnostic Information**: For diagnosing and troubleshooting, use the `info` command to display environment and version information:

   .. code-block:: bash

       stackql-deploy info

   This command will display the version of stackql-deploy, the version of StackQL used, and other pertinent system information, aiding in diagnostics and support.

What’s Next?
------------

- Explore :ref:`manifest-file` to learn how to use a manifest file to define and manage your resources.
- Check out :ref:`deploy`, :ref:`test`, and :ref:`teardown` to learn how to use stackql-deploy for deploying, testing, and safely removing your cloud infrastructure.

.. _stackql: https://github.com/stackql/stackql
