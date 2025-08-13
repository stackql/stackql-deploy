# cmd/build.py
import datetime
from ..lib.utils import (
    catch_error_and_exit,
    export_vars,
    run_ext_script,
    get_type
)
from ..lib.config import get_full_context, render_value
from ..lib.templating import get_queries, render_inline_template
from .base import StackQLBase

class StackQLProvisioner(StackQLBase):

    def process_script_resource(self, resource, dry_run, full_context):
        self.logger.info(f"running script for {resource['name']}...")
        script_template = resource.get('run', None)
        if not script_template:
            catch_error_and_exit("script resource must include 'run' key", self.logger)

        script = self.env.from_string(script_template).render(full_context)

        if dry_run:
            dry_run_script = script.replace('""', '"<evaluated>"')
            self.logger.info(f"dry run script for [{resource['name']}]:\n\n{dry_run_script}\n")
        else:
            self.logger.info(f"running script for [{resource['name']}]...")
            try:
                ret_vars = run_ext_script(script, self.logger, resource.get('exports', None))
                if resource.get('exports', None):
                    self.logger.info(f"exported variables from script: {ret_vars}")
                    export_vars(self, resource, ret_vars, resource.get('exports', []), resource.get('protected', []))
            except Exception as e:
                catch_error_and_exit(f"script failed: {e}", self.logger)

    def run(self, dry_run, show_queries, on_failure):

        start_time = datetime.datetime.now()

        self.logger.info(
            f"deploying [{self.stack_name}] in [{self.stack_env}] environment {'(dry run)' if dry_run else ''}"
        )

        for resource in self.manifest.get('resources', []):

            type = get_type(resource, self.logger)

            self.logger.info(f"processing resource [{resource['name']}], type: {type}")

            # get full context
            full_context = get_full_context(self.env, self.global_context, resource, self.logger)

            # Check if the resource has an 'if' condition and evaluate it
            if 'if' in resource:
                condition = resource['if']
                try:
                    # Render the condition with the full context to resolve any template variables
                    rendered_condition = render_value(self.env, condition, full_context, self.logger)
                    # Evaluate the condition
                    condition_result = eval(rendered_condition)
                    if not condition_result:
                        self.logger.info(f"skipping resource [{resource['name']}] due to condition: {condition}")
                        continue
                except Exception as e:
                    catch_error_and_exit(
                        f"error evaluating condition for resource [{resource['name']}]: {e}",
                        self.logger
                    )

            if type == 'script':
                self.process_script_resource(resource, dry_run, full_context)
                continue

            #
            # get resource queries
            #
            if (type == 'command' or type == 'query') and 'sql' in resource:
                # inline SQL specified in the resource
                resource_queries = {}
                inline_query = render_inline_template(self.env,
                                                        resource["name"],
                                                        resource["sql"],
                                                        full_context,
                                                        self.logger)
            else:
                resource_queries = get_queries(self.env,
                                               self.stack_dir,
                                               'resources',
                                               resource,
                                               full_context,
                                               self.logger)

            # provisioning queries
            if type in ('resource', 'multi'):
                # createorupdate queries supercede create and update queries
                createorupdate_query = resource_queries.get('createorupdate', {}).get('rendered')
                createorupdate_retries = resource_queries.get('createorupdate', {}).get('options', {}).get('retries', 1)
                createorupdate_retry_delay = resource_queries.get(
                    'createorupdate', {}).get('options', {}).get('retry_delay', 0)

                if not createorupdate_query:
                    create_query = resource_queries.get('create', {}).get('rendered')
                    create_retries = resource_queries.get('create', {}).get('options', {}).get('retries', 1)
                    create_retry_delay = resource_queries.get('create', {}).get('options', {}).get('retry_delay', 0)

                    update_query = resource_queries.get('update', {}).get('rendered')
                    update_retries = resource_queries.get('update', {}).get('options', {}).get('retries', 1)
                    update_retry_delay = resource_queries.get('update', {}).get('options', {}).get('retry_delay', 0)
                else:
                    create_query = createorupdate_query
                    create_retries = createorupdate_retries
                    create_retry_delay = createorupdate_retry_delay
                    update_query = createorupdate_query
                    update_retries = createorupdate_retries
                    update_retry_delay = createorupdate_retry_delay

                if not create_query:
                    catch_error_and_exit(
                        "iql file must include either 'create' or 'createorupdate' anchor.",
                        self.logger
                    )

            # test queries
            exists_query = resource_queries.get('exists', {}).get('rendered')
            exists_retries = resource_queries.get('exists', {}).get('options', {}).get('retries', 1)
            exists_retry_delay = resource_queries.get('exists', {}).get('options', {}).get('retry_delay', 0)

            statecheck_query = resource_queries.get('statecheck', {}).get('rendered')
            statecheck_retries = resource_queries.get('statecheck', {}).get('options', {}).get('retries', 1)
            statecheck_retry_delay = resource_queries.get('statecheck', {}).get('options', {}).get('retry_delay', 0)

            exports_query = resource_queries.get('exports', {}).get('rendered')
            exports_retries = resource_queries.get('exports', {}).get('options', {}).get('retries', 1)
            exports_retry_delay = resource_queries.get('exports', {}).get('options', {}).get('retry_delay', 0)

            if type == 'query' and not exports_query:
                if 'sql' in resource:
                    exports_query = inline_query
                    exports_retries = 1
                    exports_retry_delay = 0
                else:
                    catch_error_and_exit(
                        "inline sql must be supplied or an iql file must be present with an "
                        "'exports' anchor for query type resources.",
                        self.logger
                    )

            if type in ('resource', 'multi'):

                ignore_errors = False
                resource_exists = False
                is_correct_state = False
                if type == 'multi':
                    # multi resources ignore errors on create or update
                    ignore_errors  = True

                #
                # exists check
                #
                if createorupdate_query:
                    pass
                else:
                    if exists_query:
                        resource_exists = self.check_if_resource_exists(
                            resource_exists,
                            resource,
                            full_context,
                            exists_query,
                            exists_retries,
                            exists_retry_delay,
                            dry_run,
                            show_queries
                        )
                    elif statecheck_query:
                        # statecheck can be used as an exists check
                        is_correct_state = self.check_if_resource_is_correct_state(
                            is_correct_state,
                            resource,
                            full_context,
                            statecheck_query,
                            statecheck_retries,
                            statecheck_retry_delay,
                            dry_run,
                            show_queries
                        )
                        resource_exists = is_correct_state
                    else:
                        catch_error_and_exit("iql file must include a 'statecheck' anchor.", self.logger)

                    #
                    # state check
                    #
                    if resource_exists and not is_correct_state:
                        # bypass state check if skip_validation is set to true
                        if resource.get('skip_validation', False):
                            self.logger.info(
                                f"skipping validation for [{resource['name']}] as skip_validation is set to true."
                            )
                            is_correct_state = True
                        elif statecheck_query:
                            is_correct_state = self.check_if_resource_is_correct_state(
                                is_correct_state,
                                resource,
                                full_context,
                                statecheck_query,
                                statecheck_retries,
                                statecheck_retry_delay,
                                dry_run,
                                show_queries
                            )

                #
                # resource does not exist
                #
                is_created_or_updated = False
                if not resource_exists:
                    is_created_or_updated = self.create_resource(
                        is_created_or_updated,
                        resource,
                        full_context,
                        create_query,
                        create_retries,
                        create_retry_delay,
                        dry_run,
                        show_queries,
                        ignore_errors
                    )

                #
                # resource exists but is not in the correct state
                #
                if resource_exists and not is_correct_state:
                    is_created_or_updated = self.update_resource(
                        is_created_or_updated,
                        resource,
                        full_context,
                        update_query,
                        update_retries,
                        update_retry_delay,
                        dry_run,
                        show_queries,
                        ignore_errors
                    )

                #
                # check state again after create or update
                #
                if is_created_or_updated:
                    is_correct_state = self.check_if_resource_is_correct_state(
                        is_correct_state,
                        resource,
                        full_context,
                        statecheck_query,
                        statecheck_retries,
                        statecheck_retry_delay,
                        dry_run,
                        show_queries,
                    )

                #
                # statecheck check complete
                #
                if not is_correct_state:
                    if not dry_run:
                        catch_error_and_exit(
                            f"❌ deployment failed for {resource['name']} after post-deploy checks.",
                            self.logger
                        )

            if type == 'command':
                # command queries
                if 'sql' in resource:
                    command_query = inline_query
                    command_retries = 1
                    command_retry_delay = 0
                else:
                    # SQL from file
                    command_query = resource_queries.get('command', {}).get('rendered')
                    command_retries = resource_queries.get('command', {}).get('options', {}).get('retries', 1)
                    command_retry_delay = resource_queries.get('command', {}).get('options', {}).get('retry_delay', 0)
                if not command_query:
                    error_msg = (
                        "'sql' should be defined in the resource or the 'command' anchor "
                        "needs to be supplied in the corresponding iql file for command "
                        "type resources."
                    )
                    catch_error_and_exit(error_msg, self.logger)

                self.run_command(command_query, command_retries, command_retry_delay, dry_run, show_queries)
            #
            # exports
            #
            if exports_query:
                self.process_exports(
                    resource,
                    full_context,
                    exports_query,
                    exports_retries,
                    exports_retry_delay,
                    dry_run,
                    show_queries
                )

            if not dry_run:
                if type == 'resource':
                    self.logger.info(f"✅ successfully deployed {resource['name']}")
                elif type == 'query':
                    self.logger.info(f"✅ successfully exported variables for query in {resource['name']}")

        elapsed_time = datetime.datetime.now() - start_time
        self.logger.info(f"deployment completed in {elapsed_time}")
