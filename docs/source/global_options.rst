Global Options for stackql-deploy
=================================

**stackql-deploy** provides several global options that can be used with any of the commands (`build`, `test`, `teardown`). These options allow you to customize the behavior of the tool according to your needs, such as setting the logging level or specifying an environment file.

Available Global Options
------------------------

The following are the global options available in **stackql-deploy**:

- **--log-level**
- **--env-file**
- **-e, --env**
- **--dry-run**
- **--on-failure**

.. note::
   These options can be combined with any command to alter the behavior of **stackql-deploy**.

**--log-level**
---------------

Sets the logging level for the operation. This determines the verbosity of the output during command execution.

.. code-block:: bash

    --log-level DEBUG

Valid options include:

- ``DEBUG``: Provides detailed logging for troubleshooting.
- ``INFO``: Gives informational messages about the process.
- ``WARNING``: Outputs only warnings and errors.
- ``ERROR``: Shows only error messages.
- ``CRITICAL``: Logs critical errors only.

**Example**:

.. code-block:: bash

    stackql-deploy build prod ./my_project --log-level INFO

**--env-file**
---------------

Specifies a custom environment file that contains environment variables to be loaded before executing a command.

.. code-block:: bash

    --env-file path/to/custom.env

**Example**:

.. code-block:: bash

    stackql-deploy test dev ./my_project --env-file .env.production

**-e, --env**
-------------

Allows you to specify additional environment variables directly on the command line. This is useful for overriding values in the environment file or providing variables that are only needed occasionally.

.. code-block:: bash

    -e KEY=value -e ANOTHER_KEY=another_value

**Example**:

.. code-block:: bash

    stackql-deploy teardown prod ./my_project -e API_KEY=12345 -e FEATURE_FLAG=enabled

**--dry-run**
-------------

Executes the command without making any changes to the actual resources. This is particularly useful for testing to see what actions the tool would take without applying them.

.. code-block:: bash

    --dry-run

**Example**:

.. code-block:: bash

    stackql-deploy build prod ./my_project --dry-run

**--on-failure**
----------------

Defines the action to take if the command encounters an error. This option helps manage the failure behavior, particularly in automated scripts or pipelines.

Valid options are:

- ``rollback``: Attempts to revert changes to the previous state.
- ``ignore``: Continues execution, ignoring the error.
- ``error``: Stops execution and exits with an error status.

.. code-block:: bash

    --on-failure rollback

**Example**:

.. code-block:: bash

    stackql-deploy build prod ./my_project --on-failure ignore

Using Global Options
--------------------

Combine these options as needed to customize the execution of **stackql-deploy** commands. For example:

.. code-block:: bash

    stackql-deploy build prod ./my_project --env-file .env.production --log-level DEBUG --dry-run

This command would initiate a dry run of deploying the `./my_project` with a production environment file, with detailed debug logging enabled.

Summary
-------

Understanding and utilizing the global options in **stackql-deploy** can significantly enhance your control and flexibility when managing deployments. These options allow you to tailor the tool's operation to fit your specific workflow and environmental requirements.
