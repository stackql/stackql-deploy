from ..lib.utils import (
    perform_retries,
    run_stackql_command,
    catch_error_and_exit,
    run_stackql_query,
    export_vars,
    show_query,
    check_all_dicts,
)
from ..lib.config import setup_environment, load_manifest, get_global_context_and_providers

class StackQLBase:
    def __init__(self, stackql, vars, logger, stack_dir, stack_env):
        self.stackql = stackql
        self.vars = vars
        self.logger = logger
        self.stack_dir = stack_dir
        self.stack_env = stack_env
        self.env = setup_environment(self.stack_dir, self.logger)
        self.manifest = load_manifest(self.stack_dir, self.logger)
        self.stack_name = self.manifest.get('name', stack_dir)
        self.global_context, self.providers = get_global_context_and_providers(
            self.env,
            self.manifest,
            self.vars,
            self.stack_env,
            self.stack_name,
            self.stackql,
            self.logger
        )

    def process_custom_auth(
            self,
            resource,
            full_context
    ):
        custom_auth = resource.get('auth', {})
        env_vars = {}

        if custom_auth:
            self.logger.info(f"🔑 custom auth is configured for [{resource['name']}]")

            # Function to recursively search for keys of interest and populate env_vars
            def extract_env_vars(auth_config):
                for key, value in auth_config.items():
                    if key in {"username_var", "password_var", "credentialsenvvar", "keyIDenvvar"}:
                        # Retrieve the variable's value from full_context
                        env_var_name = value
                        env_var_value = full_context.get(env_var_name)
                        if env_var_value:
                            env_vars[env_var_name] = env_var_value
                    elif isinstance(value, dict):
                        # Recursively check nested dictionaries
                        extract_env_vars(value)

            # Start extracting env vars from custom_auth
            extract_env_vars(custom_auth)

        # If no custom auth, return None for both custom_auth and env_vars
        return (custom_auth if custom_auth else None, env_vars if env_vars else None)

    def process_exports(
        self,
        resource,
        full_context,
        exports_query,
        exports_retries,
        exports_retry_delay,
        dry_run,
        show_queries,
        ignore_missing_exports=False
    ):
        expected_exports = resource.get('exports', [])

        # Check if all items in expected_exports are dictionaries
        all_dicts = check_all_dicts(expected_exports, self.logger)

        if len(expected_exports) > 0:
            protected_exports = resource.get('protected', [])
            if dry_run:
                export_data = {}
                if all_dicts:
                    for item in expected_exports:
                        for _, val in item.items():
                            # when item is a dictionary,
                            # val(expected_exports) is the key to be exported
                            export_data[val] = "<evaluated>"
                else:
                    # when item is not a dictionary,
                    # item is the key to be exported
                    for item in expected_exports:
                        export_data[item] = "<evaluated>"
                export_vars(self, resource, export_data, expected_exports, protected_exports)
                self.logger.info(
                    f"📦 dry run exports query for [{resource['name']}]:\n\n/* exports query */\n{exports_query}\n"
                )
            else:
                self.logger.info(f"📦 exporting variables for [{resource['name']}]...")
                show_query(show_queries, exports_query, self.logger)
                custom_auth, env_vars = self.process_custom_auth(resource, full_context)
                exports = run_stackql_query(
                    exports_query,
                    self.stackql,
                    True,
                    self.logger,
                    custom_auth=custom_auth,
                    env_vars=env_vars,
                    retries=exports_retries,
                    delay=exports_retry_delay
                )
                self.logger.debug(f"exports: {exports}")

                if (exports is None or len(exports) == 0):
                    if ignore_missing_exports:
                        return
                    else:
                        show_query(True, exports_query, self.logger)
                        catch_error_and_exit(f"exports query failed for {resource['name']}", self.logger)

                if len(exports) > 1:
                    catch_error_and_exit(
                        f"exports should include one row only, received {str(len(exports))} rows",
                        self.logger
                    )

                if len(exports) == 1 and not isinstance(exports[0], dict):
                    catch_error_and_exit(f"exports must be a dictionary, received {str(exports[0])}", self.logger)

                export = exports[0]
                if len(exports) == 0:
                    export_data = {}
                    if all_dicts:
                        for item in expected_exports:
                            for key, val in item.items():
                                export_data[val] = ''
                    else:
                        export_data[item] = ''
                else:
                    export_data = {}
                    for item in expected_exports:
                        if all_dicts:
                            for key, val in item.items():
                                # when item is a dictionary,
                                # compare key(expected_exports) with key(export)
                                # set val(expected_exports) as key and export[key] as value in export_data
                                if isinstance(export.get(key), dict) and 'String' in export[key]:
                                    export_data[val] = export[key]['String']
                                else:
                                    export_data[val] = export.get(key, '')
                        else:
                            if isinstance(export.get(item), dict) and 'String' in export[item]:
                                export_data[item] = export[item]['String']
                            else:
                                export_data[item] = export.get(item, '')
                export_vars(self, resource, export_data, expected_exports, all_dicts, protected_exports)

    def check_if_resource_exists(
        self,
        resource_exists,
        resource,
        full_context,
        exists_query,
        exists_retries,
        exists_retry_delay,
        dry_run,
        show_queries,
        delete_test=False
    ):
        check_type = 'exists'
        if delete_test:
            check_type = 'post-delete'
        if exists_query:
            if dry_run:
                self.logger.info(
                    f"🔎 dry run {check_type} check for [{resource['name']}]:\n\n/* exists query */\n{exists_query}\n"
                )
            else:
                self.logger.info(f"🔎 running {check_type} check for [{resource['name']}]...")
                show_query(show_queries, exists_query, self.logger)
                custom_auth, env_vars = self.process_custom_auth(resource, full_context)
                resource_exists = perform_retries(
                    resource,
                    exists_query,
                    exists_retries,
                    exists_retry_delay,
                    self.stackql,
                    self.logger,
                    delete_test,
                    custom_auth=custom_auth,
                    env_vars=env_vars
                )
        else:
            self.logger.info(f"{check_type} check not configured for [{resource['name']}]")
            if delete_test:
                resource_exists = False
        return resource_exists

    def check_if_resource_is_correct_state(
        self,
        is_correct_state,
        resource,
        full_context,
        statecheck_query,
        statecheck_retries,
        statecheck_retry_delay,
        dry_run,
        show_queries
    ):
        if statecheck_query:
            if dry_run:
                self.logger.info(
                    f"🔎 dry run state check for [{resource['name']}]:\n\n/* state check query */\n{statecheck_query}\n"
                )
            else:
                self.logger.info(f"🔎 running state check for [{resource['name']}]...")
                show_query(show_queries, statecheck_query, self.logger)
                custom_auth, env_vars = self.process_custom_auth(resource, full_context)
                is_correct_state = perform_retries(
                    resource,
                    statecheck_query,
                    statecheck_retries,
                    statecheck_retry_delay,
                    self.stackql,
                    self.logger,
                    False,
                    custom_auth=custom_auth,
                    env_vars=env_vars
                )
                if is_correct_state:
                    self.logger.info(f"👍 [{resource['name']}] is in the desired state")
                else:
                    self.logger.info(f"👎 [{resource['name']}] is not in the desired state")
        else:
            self.logger.info(f"state check not configured for [{resource['name']}]")
            is_correct_state = True
        return is_correct_state

    def create_resource(
        self,
        is_created_or_updated,
        resource,
        full_context,
        create_query,
        create_retries,
        create_retry_delay,
        dry_run,
        show_queries,
        ignore_errors=False
    ):
        if dry_run:
            self.logger.info(
                f"🚧 dry run create for [{resource['name']}]:\n\n/* insert (create) query */\n{create_query}\n"
            )
        else:
            self.logger.info(f"[{resource['name']}] does not exist, creating 🚧...")
            show_query(show_queries, create_query, self.logger)
            custom_auth, env_vars = self.process_custom_auth(resource, full_context)
            msg = run_stackql_command(
                create_query,
                self.stackql,
                self.logger,
                custom_auth=custom_auth,
                env_vars=env_vars,
                ignore_errors=ignore_errors,
                retries=create_retries,
                retry_delay=create_retry_delay
            )
            self.logger.debug(f"create response: {msg}")
            is_created_or_updated = True
        return is_created_or_updated

    def update_resource(
        self,
        is_created_or_updated,
        resource,
        full_context,
        update_query,
        update_retries,
        update_retry_delay,
        dry_run,
        show_queries,
        ignore_errors=False
    ):
        if update_query:
            if dry_run:
                self.logger.info(f"🚧 dry run update for [{resource['name']}]:\n\n/* update query */\n{update_query}\n")
            else:
                self.logger.info(f"🔧 updating [{resource['name']}]...")
                show_query(show_queries, update_query, self.logger)
                custom_auth, env_vars = self.process_custom_auth(resource, full_context)
                msg = run_stackql_command(
                    update_query,
                    self.stackql,
                    self.logger,
                    custom_auth=custom_auth,
                    env_vars=env_vars,
                    ignore_errors=ignore_errors,
                    retries=update_retries,
                    retry_delay=update_retry_delay
                )
                self.logger.debug(f"update response: {msg}")
                is_created_or_updated = True
        else:
            self.logger.info(f"update query not configured for [{resource['name']}], skipping update...")
        return is_created_or_updated

    def delete_resource(
        self,
        resource,
        full_context,
        delete_query,
        delete_retries,
        delete_retry_delay,
        dry_run,
        show_queries,
        ignore_errors=False,
    ):
        if delete_query:
            if dry_run:
                self.logger.info(f"🚧 dry run delete for [{resource['name']}]:\n\n{delete_query}\n")
            else:
                self.logger.info(f"🚧 deleting [{resource['name']}]...")
                show_query(show_queries, delete_query, self.logger)
                custom_auth, env_vars = self.process_custom_auth(resource, full_context)
                msg = run_stackql_command(
                    delete_query,
                    self.stackql,
                    self.logger,
                    custom_auth=custom_auth,
                    env_vars=env_vars,
                    ignore_errors=ignore_errors,
                    retries=delete_retries,
                    retry_delay=delete_retry_delay
                )
                self.logger.debug(f"delete response: {msg}")
        else:
            self.logger.info(f"delete query not configured for [{resource['name']}], skipping delete...")

    def run_command(self, command_query, command_retries, command_retry_delay, dry_run, show_queries):
        if command_query:
            if dry_run:
                self.logger.info(f"🚧 dry run command:\n\n{command_query}\n")
            else:
                self.logger.info("🚧 running command...")
                show_query(show_queries, command_query, self.logger)
                run_stackql_command(
                    command_query,
                    self.stackql,
                    self.logger,
                    retries=command_retries,
                    retry_delay=command_retry_delay
                )
        else:
            self.logger.info("command query not configured, skipping command...")