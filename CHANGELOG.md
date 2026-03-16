# Changelog

## 1.9.4 (2025-10-16)

- added `--output-file` argument
- added stack level `exports` - pre defined `stack_name`, `stack_env`, `elapsed_time` and user defined
- Added performance enhancement query strategy
- Added tab completion
- Added enhanced logging decorators

## 1.8.6 (2025-07-22)

- Added support for inline `sql` for `command` and `query` resource types
- Added `sql_escape` filter

## 1.8.5 (2025-06-30)

- Added support for resource scoped variables
- Added developer credits in `info`

## 1.8.3 (2025-02-08)

- Added walkthrough for databricks bootstrap on aws.
- Bugfix for export variables on dry run.

## 1.8.2 (2025-01-16)

- Added timing output for `build`, `test` and `teardown` operations

## 1.8.1 (2025-01-11)

- Added `uuid()` templating function
- Exports evaluation optimization for teardown operations 

## 1.8.0 (2024-11-09)

- Added option for command specific authentication

## 1.7.7 (2024-10-09)

- Supported version pinning for providers(aws, gcp, azure and etc) in `manifest` file

## 1.7.6 (2024-10-07)

- Added support for named `exports` (assigning an alias to the column name in the resource query file) - allows for more generalization and reuse of query files

## 1.7.5 (2024-09-28)

- Renamed the variable `vars` to `env_vars` for clarity and consistency

## 1.7.4 (2024-09-19)

- Colorizing the headings in `stack-deploy info` to green

## 1.7.3 (2024-09-18)

- Grouping information into logical sections: `StackQL Deploy CLI`, `StackQL Library`, and `Installed Providers` for `info` command.

## 1.7.2 (2024-09-14)

- Fixed issue with missing `stackql_manifest.yml.template` by updating `MANIFEST.in` to include template files

## v1.7.1 (2024-09-03)

- fixed `teardown` issue

## v1.7.0 (2024-09-02)

- changed `preflight` to `exists` and `postdeploy` to `statecheck`, maintaining backwards compatibility
- enhanced `multi` resource support

## v1.6.5 (2024-08-31)

- added `multi` type
- added support for `create` retries

## v1.6.4 (2024-08-29)

- added `from_json` filter
- additional error handling for method signature mismatches

## v1.6.3 (2024-08-21)

- `createorupdate` skipped if checks pass

## v1.6.2 (2024-08-18)

- added `shell` command to launch a `stackql shell`

## v1.6.1 (2024-08-17)

- removed un-needed env vars from the global context

## v1.6.0 (2024-07-23)

- added support for AWS Cloud Control `PatchDocument` creation for `UPDATE` statements

## v1.5.3 (2024-06-05)

- templating fixes

## v1.5.0 (2024-04-30)

- added `script` resource type

## v1.2.0 (2024-04-23)

- added `exports` anchor
- support for runtime stack variables

## v1.0.26 (2024-04-18)

- added `init` function
- added templates
- improved exception handling

## v1.0.0 (2024-04-16)

### Initial Release

- basic support for `build`, `test` and `teardown` functions
- added `info` diagnostic functions
