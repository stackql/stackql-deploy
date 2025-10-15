---
id: github-actions
title: GitHub Actions - StackQL Deploy
hide_title: false
hide_table_of_contents: false
description: Documentation for using the StackQL Deploy GitHub Action to automate infrastructure deployment and testing.
tags: []
draft: false
unlisted: false
---

# `stackql-deploy` GitHub Action

The [`stackql-deploy` GitHub Action](https://github.com/marketplace/actions/stackql-deploy) allows you to execute `stackql-deploy` commands to deploy or test a stack within your CI/CD pipelines in a GitHub Actions workflow.

## Usage

The `stackql-deploy` GitHub Action will pull the latest `stackql-deploy` package from the [PyPi repository](https://pypi.org/project/stackql-deploy/).  The action invokes a `stackql-deploy` command with `inputs` (detailed below).  Here is a basic examplf of using the `stackql-deploy` GitHub Action in a workflow.

```yaml {13}
jobs:
  stackql-actions-test:
    name: StackQL Actions Test
    runs-on: ubuntu-latest
    env:
      GOOGLE_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }} # add additional cloud provider creds here as needed
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Deploy a Stack
        uses: stackql/setup-deploy@v1.0.1
        with:
          command: 'build'
          stack_dir: 'examples/k8s-the-hard-way'
          stack_env: 'dev'
          env_vars: 'GOOGLE_PROJECT=stackql-k8s-the-hard-way-demo'        
```            

:::note[Provider Authentication]

Authentication to StackQL providers is managed through environment variables sourced from GitHub Actions Secrets. Ensure you configure the necessary secrets in your repository settings to authenticate with your cloud provider(s).  

For more information on provider-specific authentication, refer to the setup instructions available in the [StackQL Provider Registry Docs](https://github.com/stackql/stackql-provider-registry).

:::


## Inputs

The following inputs can be configured for the `stackql-deploy` GitHub Action:

| Input            | Description                                                                 | Example                                           |
|------------------|-----------------------------------------------------------------------------|---------------------------------------------------|
| `command`        | The `stackql-deploy` command to run (`build` or `test`)                     | `build`                                           |
| `stack_dir`      | The repository directory containing `stackql_manifest.yml` and resources    | `examples/k8s-the-hard-way`                       |
| `stack_env`      | The environment to deploy or test (e.g., `dev`, `prod`)                     | `dev`                                             |
| `env_vars`       | (Optional) Environment variables or secrets to import into a stack          | `GOOGLE_PROJECT=stackql-k8s-the-hard-way-demo`    |
| `env_file`       | (Optional) Environment variables sourced from a file                        | `.env.prod`                                       |
| `output_file`    | (Optional) File path to export deployment variables as JSON                 | `./outputs/deployment.json`                      |
| `show_queries`   | (Optional) Show the queries executed in the output logs                     | `true`                                            |
| `log_level`      | (Optional) Set the logging level (`INFO` or `DEBUG`, defaults to `INFO`)    | `DEBUG`                                           |
| `dry_run`        | (Optional) Perform a dry run of the operation                                | `true`                                            |
| `custom_registry`| (Optional) Custom registry URL to be used for StackQL                       | `https://myreg`                                   |
| `on_failure`     | (Optional) Action to take on failure (not implemented yet)                  | `rollback`                                        |

## Examples

### Deploy a Stack

This example shows how to build a stack (located in `examples/k8s-the-hard-way`) for a development (`dev`) environment:

```yaml
jobs:
  stackql-actions-test:
    name: StackQL Actions Test
    runs-on: ubuntu-latest
    env:
      GOOGLE_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }} # add additional cloud provider creds here as needed
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Deploy a Stack
        uses: stackql/setup-deploy@v1.0.1
        with:
          command: 'build'
          stack_dir: 'examples/k8s-the-hard-way'
          stack_env: 'dev'
          env_vars: 'GOOGLE_PROJECT=stackql-k8s-the-hard-way-demo'
```

### Test a Stack

This example shows how to test a stack for a staging (`sit`) environment:

```yaml
jobs:
  stackql-actions-test:
    name: StackQL Actions Test
    runs-on: ubuntu-latest
    env:
      GOOGLE_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }} # add additional cloud provider creds here as needed
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Test a Stack
        uses: stackql/setup-deploy@v1.0.1
        with:
          command: 'test'
          stack_dir: 'examples/k8s-the-hard-way'
          stack_env: 'sit'
          env_vars: 'GOOGLE_PROJECT=stackql-k8s-the-hard-way-demo'
```

### Deploy and Export Variables

This example shows how to deploy a stack and export deployment variables to a JSON file for use in subsequent workflow steps:

```yaml
jobs:
  deploy-and-process:
    name: Deploy Stack and Process Outputs
    runs-on: ubuntu-latest
    env:
      DATABRICKS_CLIENT_ID: ${{ secrets.DATABRICKS_CLIENT_ID }}
      DATABRICKS_CLIENT_SECRET: ${{ secrets.DATABRICKS_CLIENT_SECRET }}
      AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
      AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Deploy Databricks Stack
        uses: stackql/setup-deploy@v1.0.1
        with:
          command: 'build'
          stack_dir: 'examples/databricks/serverless'
          stack_env: 'prod'
          output_file: './deployment-outputs.json'
          env_vars: |
            DATABRICKS_ACCOUNT_ID=${{ secrets.DATABRICKS_ACCOUNT_ID }}
            AWS_REGION=us-east-1
            AWS_ACCOUNT_ID=${{ secrets.AWS_ACCOUNT_ID }}

      - name: Parse Deployment Outputs
        id: parse_outputs
        run: |
          echo "workspace_name=$(jq -r '.databricks_workspace_name' ./deployment-outputs.json)" >> $GITHUB_OUTPUT
          echo "workspace_id=$(jq -r '.databricks_workspace_id' ./deployment-outputs.json)" >> $GITHUB_OUTPUT
          echo "workspace_status=$(jq -r '.workspace_status' ./deployment-outputs.json)" >> $GITHUB_OUTPUT

      - name: Use Exported Variables
        run: |
          echo "Deployed workspace: ${{ steps.parse_outputs.outputs.workspace_name }}"
          echo "Workspace ID: ${{ steps.parse_outputs.outputs.workspace_id }}"
          echo "Status: ${{ steps.parse_outputs.outputs.workspace_status }}"
```
