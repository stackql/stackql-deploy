from ..lib.utils import (
    perform_retries,
    run_stackql_command,
    catch_error_and_exit,
    export_vars,
    run_ext_script,
    show_query,
    get_type
)
from ..lib.config import get_full_context
from ..lib.templating import get_queries
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

        self.logger.info(f"deploying [{self.stack_name}] in [{self.stack_env}] environment {'(dry run)' if dry_run else ''}")

        for resource in self.manifest.get('resources', []):

            type = get_type(resource, self.logger)

            self.logger.info(f"processing resource [{resource['name']}], type: {type}")

            # get full context
            full_context = get_full_context(self.env, self.global_context, resource, self.logger)    

            if type == 'script':
                self.process_script_resource(resource, dry_run, full_context)
                continue

            #
            # get resource queries
            #
            resource_queries = get_queries(self.env, self.stack_dir, 'resources', resource, full_context, self.logger)

            # provisioning queries
            if type in ('resource', 'multi'):
                # createorupdate queries supercede create and update queries
                createorupdate_query = resource_queries.get('createorupdate', {}).get('rendered')
                createorupdate_retries = resource_queries.get('createorupdate', {}).get('options', {}).get('retries', 1)
                createorupdate_retry_delay = resource_queries.get('createorupdate', {}).get('options', {}).get('retry_delay', 0)

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
                    catch_error_and_exit("iql file must include either 'create' or 'createorupdate' anchor.", self.logger)

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
                catch_error_and_exit("iql file must include 'exports' anchor for query type resources.", self.logger)

            if type in ('resource', 'multi'):

                #
                # run exists check (check if resource exists)
                #
                if exists_query:
                    if dry_run:
                        self.logger.info(f"🔎 dry run exists check for [{resource['name']}]:\n\n/* exists query */\n{exists_query}\n")
                    else:
                        self.logger.info(f"🔎 running exists check for [{resource['name']}]...")
                        show_query(show_queries, exists_query, self.logger)
                        resource_exists = perform_retries(resource, exists_query, exists_retries, exists_retry_delay, self.stackql, self.logger)
                else:
                    self.logger.info(f"exists check not configured for [{resource['name']}]")
                    resource_exists = False
                
                #
                # initial state check (if resource exists)
                #
                if resource_exists:
                    if not statecheck_query:
                        self.logger.info(f"state check not configured for [{resource['name']}], state check bypassed...")
                        is_correct_state = True
                    else:
                        self.logger.info(f"🔎 [{resource['name']}] exists, running state check...")
                        show_query(show_queries, statecheck_query, self.logger)
                        is_correct_state = perform_retries(resource, statecheck_query, statecheck_retries, statecheck_retry_delay, self.stackql, self.logger)

                # if exists and correct state, skip deploy
                if resource_exists and is_correct_state:
                    self.logger.info(f"👍 [{resource['name']}] is in the desired state, skipping create or update...")

                #
                # resource does not exist
                #
                if not resource_exists:
                    if dry_run:
                        self.logger.info(f"🚧 dry run create for [{resource['name']}]:\n\n/* insert (create) query */\n{create_query}\n")
                    else:
                        self.logger.info(f"[{resource['name']}] does not exist, creating 🚧...")
                        show_query(show_queries, create_query, self.logger)
                        msg = run_stackql_command(create_query, self.stackql, self.logger, ignore_errors=False, retries=create_retries, retry_delay=create_retry_delay)
                        self.logger.debug(f"create response: {msg}")

                #
                # resource exists but is not in the correct state
                #
                if resource_exists and not is_correct_state:
                    if dry_run:
                        self.logger.info(f"🚧 dry run update for [{resource['name']}]:\n\n/* update query */\n{update_query}\n")
                    else:
                        self.logger.info(f"🔧 updating [{resource['name']}]...")
                        show_query(show_queries, update_query, self.logger)
                        msg = run_stackql_command(update_query, self.stackql, self.logger, ignore_errors=False, retries=update_retries, retry_delay=update_retry_delay)
                        self.logger.debug(f"update response: {msg}")

                #
                # check state again after create or update
                #
                if dry_run:
                    self.logger.info(f"🔎 dry run post create/update state check for [{resource['name']}]:\n\n/* state check query */\n{statecheck_query}\n")
                else:
                    self.logger.info(f"🔎 running post create/update state check for [{resource['name']}]...")
                    show_query(show_queries, statecheck_query, self.logger)
                    is_correct_state = perform_retries(resource, statecheck_query, statecheck_retries, statecheck_retry_delay, self.stackql, self.logger)
                   
                #
                # statecheck check complete
                #
                if not is_correct_state:
                    if not dry_run:
                        catch_error_and_exit(f"❌ deployment failed for {resource['name']} after post-deploy checks.", self.logger)

            #
            # exports
            #
            if exports_query:
                self.process_exports(resource, exports_query, exports_retries, exports_retry_delay, dry_run, show_queries)

            if not dry_run:
                if type == 'resource':
                    self.logger.info(f"✅ successfully deployed {resource['name']}")
                elif type == 'query':
                    self.logger.info(f"✅ successfully exported variables for query in {resource['name']}")
