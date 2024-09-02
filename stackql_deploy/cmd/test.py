from ..lib.utils import (
    perform_retries,
    catch_error_and_exit,
    show_query,
    get_type
)
from ..lib.config import get_full_context
from ..lib.templating import get_queries
from .base import StackQLBase

class StackQLTestRunner(StackQLBase):

    def run(self, dry_run, show_queries, on_failure):
        
        self.logger.info(f"testing [{self.stack_name}] in [{self.stack_env}] environment {'(dry run)' if dry_run else ''}")

        for resource in self.manifest.get('resources', []):

            type = get_type(resource, self.logger)

            if type == 'query':
                self.logger.info(f"exporting variables for [{resource['name']}]")
            elif type in ('resource', 'multi'):
                self.logger.info(f"testing resource [{resource['name']}], type: {type}")
            else:
                catch_error_and_exit(f"unknown resource type: {type}", self.logger)

            # get full context
            full_context = get_full_context(self.env, self.global_context, resource, self.logger)    

            #
            # get test queries
            #
            test_queries = get_queries(self.env, self.stack_dir, 'resources', resource, full_context, self.logger)

            statecheck_query = test_queries.get('statecheck', {}).get('rendered')
            statecheck_retries = test_queries.get('statecheck', {}).get('options', {}).get('retries', 1)
            statecheck_retry_delay = test_queries.get('statecheck', {}).get('options', {}).get('retry_delay', 0)

            exports_query = test_queries.get('exports', {}).get('rendered')
            exports_retries = test_queries.get('exports', {}).get('options', {}).get('retries', 1)
            exports_retry_delay = test_queries.get('exports', {}).get('options', {}).get('retry_delay', 0)

            if type == 'query' and not exports_query:
                catch_error_and_exit("iql file must include 'exports' anchor for query type resources.", self.logger)                              

            #
            # statecheck check
            #
            if type in ('resource', 'multi'):
                if not statecheck_query:
                    is_correct_state = True
                    self.logger.info(f"❓ test not configured for [{resource['name']}]")
                elif dry_run:
                    is_correct_state = True
                    self.logger.info(f"test query for [{resource['name']}]:\n\n{statecheck_query}\n")
                else:
                    self.logger.info(f"🔎 checking state for [{resource['name']}]...")
                    show_query(show_queries, statecheck_query, self.logger)
                    is_correct_state = perform_retries(resource, statecheck_query, statecheck_retries, statecheck_retry_delay, self.stackql, self.logger)

                if not is_correct_state:
                    catch_error_and_exit(f"❌ test failed for {resource['name']}.", self.logger)

            #
            # exports
            #
            if exports_query:
                self.process_exports(resource, exports_query, exports_retries, exports_retry_delay, dry_run, show_queries)

            if type == 'resource' and not dry_run:
                self.logger.info(f"✅ test passed for {resource['name']}")
