from ..lib.utils import (
    perform_retries,
    run_stackql_command,
    catch_error_and_exit,
    show_query,
    get_type
)
from ..lib.config import get_full_context
from ..lib.templating import get_queries
from .base import StackQLBase

class StackQLDeProvisioner(StackQLBase):

    def collect_exports(self, show_queries, dry_run):
        self.logger.info(f"collecting exports for [{self.stack_name}] in [{self.stack_env}] environment")

        for resource in self.manifest.get('resources', []):
            
            self.logger.info(f"getting exports for resource [{resource['name']}]")

            # get full context
            full_context = get_full_context(self.env, self.global_context, resource, self.logger)

            # get resource queries
            test_queries = get_queries(self.env, self.stack_dir, 'resources', resource, full_context, self.logger)

            exports_query = test_queries.get('exports', {}).get('rendered')
            exports_retries = test_queries.get('exports', {}).get('options', {}).get('retries', 1)
            exports_retry_delay = test_queries.get('exports', {}).get('options', {}).get('retry_delay', 0)

            if exports_query:
                self.process_exports(resource, exports_query, exports_retries, exports_retry_delay, dry_run, show_queries, ignore_missing_exports=True)

    def run(self, dry_run, show_queries, on_failure):

        self.logger.info(f"tearing down [{self.stack_name}] in [{self.stack_env}] environment {'(dry run)' if dry_run else ''}")

        # Collect all exports
        self.collect_exports(show_queries, dry_run)

        for resource in reversed(self.manifest['resources']):
            # process resources in reverse order
            type = get_type(resource, self.logger)

            if type not in ('resource', 'multi'):
                self.logger.debug(f"skipping resource [{resource['name']}] (type: {type})")
                continue
            else:
                self.logger.info(f"de-provisioning resource [{resource['name']}], type: {type}")

            # get full context
            full_context = get_full_context(self.env, self.global_context, resource, self.logger)    

            #
            # get resource queries
            #
            resource_queries = get_queries(self.env, self.stack_dir, 'resources', resource, full_context, self.logger)

            exists_query = resource_queries.get('exists', {}).get('rendered')
            exists_retries = resource_queries.get('exists', {}).get('options', {}).get('retries', 1)
            exists_retry_delay = resource_queries.get('exists', {}).get('options', {}).get('retry_delay', 0)
            postdelete_exists_retries = resource_queries.get('exists', {}).get('options', {}).get('postdelete_retries', 10)
            postdelete_exists_retry_delay = resource_queries.get('exists', {}).get('options', {}).get('postdelete_retry_delay', 5)

            delete_query = resource_queries.get('delete', {}).get('rendered')
            delete_retries = resource_queries.get('delete', {}).get('options', {}).get('retries', 1)
            delete_retry_delay = resource_queries.get('delete', {}).get('options', {}).get('retry_delay', 0)

            if not delete_query:
                self.logger.info(f"delete query not defined for [{resource['name']}], skipping...")
                continue                

            #
            # pre-delete check
            #
            resource_exists = False
            if type == 'multi':
                self.logger.info(f"pre-delete check not supported for multi resources, skipping...")
                resource_exists = True
            elif exists_query:
                if dry_run:
                    self.logger.info(f"🔎 dry run pre-delete check for [{resource['name']}]:\n\n{exists_query}\n")
                else:
                    self.logger.info(f"🔎 checking if [{resource['name']}] exists...")
                    show_query(show_queries, exists_query, self.logger)
                    resource_exists = perform_retries(resource, exists_query, exists_retries, exists_retry_delay, self.stackql, self.logger)
            else:
                self.logger.info(f"no exists query defined for [{resource['name']}], skipping pre-delete check...")
            
            #
            # delete
            #       
            if resource_exists:
                if dry_run:
                    self.logger.info(f"🚧 dry run delete for [{resource['name']}]:\n\n{delete_query}\n")
                else:
                    self.logger.info(f"🚧 deleting [{resource['name']}]...")
                    show_query(show_queries, delete_query, self.logger)
                    msg = run_stackql_command(delete_query, self.stackql, self.logger, ignore_errors=False, retries=delete_retries, retry_delay=delete_retry_delay)
                    self.logger.debug(f"delete response: {msg}")
            else:
                self.logger.info(f"resource [{resource['name']}] does not exist, skipping delete")
                continue

            #
            # confirm deletion
            #
            resource_deleted = False
            if dry_run:
                self.logger.info(f"🔎 dry run post-delete check for [{resource['name']}]:\n\n{exists_query}\n")
            else:
                self.logger.info(f"🔎 checking if [{resource['name']}] exists...")
                show_query(show_queries, exists_query, self.logger)
                resource_deleted = perform_retries(resource, exists_query, postdelete_exists_retries, postdelete_exists_retry_delay, self.stackql, self.logger, delete_test=True)
                if resource_deleted:
                    self.logger.info(f"✅ successfully deleted {resource['name']}")
                else:
                    catch_error_and_exit(f"❌ failed to delete {resource['name']}.", self.logger)
