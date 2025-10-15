# cmd/test.py
import datetime
from ..lib.utils import (
    catch_error_and_exit,
    get_type,
    print_unicode_box,
    BorderColor
)
from ..lib.config import get_full_context
from ..lib.templating import get_queries, render_inline_template
from .base import StackQLBase

class StackQLTestRunner(StackQLBase):
    def run(self, dry_run, show_queries, on_failure, output_file=None):

        start_time = datetime.datetime.now()

        self.logger.info(
            f"testing [{self.stack_name}] in [{self.stack_env}] environment {'(dry run)' if dry_run else ''}"
        )

        for resource in self.manifest.get('resources', []):

            print_unicode_box(f"Processing resource: [{resource['name']}]", BorderColor.BLUE)

            type = get_type(resource, self.logger)

            if type == 'query':
                self.logger.info(f"exporting variables for [{resource['name']}]")
            elif type in ('resource', 'multi'):
                self.logger.info(f"testing resource [{resource['name']}], type: {type}")
            elif type == 'command':
                continue
            else:
                catch_error_and_exit(f"unknown resource type: {type}", self.logger)

            # get full context
            full_context = get_full_context(self.env, self.global_context, resource, self.logger)

            #
            # get test queries
            #
            if type == 'query' and 'sql' in resource:
                # inline SQL specified in the resource
                test_queries = {}
                inline_query = render_inline_template(self.env,
                                                        resource["name"],
                                                        resource["sql"],
                                                        full_context,
                                                        self.logger)
            else:
                test_queries = get_queries(self.env,
                                               self.stack_dir,
                                               'resources',
                                               resource,
                                               full_context,
                                               self.logger)



            statecheck_query = test_queries.get('statecheck', {}).get('rendered')
            statecheck_retries = test_queries.get('statecheck', {}).get('options', {}).get('retries', 1)
            statecheck_retry_delay = test_queries.get('statecheck', {}).get('options', {}).get('retry_delay', 0)

            exports_query = test_queries.get('exports', {}).get('rendered')
            exports_retries = test_queries.get('exports', {}).get('options', {}).get('retries', 1)
            exports_retry_delay = test_queries.get('exports', {}).get('options', {}).get('retry_delay', 0)

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
            #
            # statecheck check with optimizations
            #
            exports_result_from_proxy = None  # Track exports result if used as proxy

            if type in ('resource', 'multi'):
                if 'skip_validation' in resource:
                    self.logger.info(f"Skipping statecheck for {resource['name']}")
                    is_correct_state = True
                else:
                    if statecheck_query:
                        is_correct_state = self.check_if_resource_is_correct_state(
                            False,
                            resource,
                            full_context,
                            statecheck_query,
                            statecheck_retries,
                            statecheck_retry_delay,
                            dry_run,
                            show_queries
                        )
                    elif exports_query:
                        # OPTIMIZATION: Use exports as statecheck proxy for test
                        self.logger.info(
                            f"🔄 using exports query as proxy for statecheck test "
                            f"for [{resource['name']}]"
                        )
                        is_correct_state, exports_result_from_proxy = self.check_state_using_exports_proxy(
                            resource,
                            full_context,
                            exports_query,
                            exports_retries,
                            exports_retry_delay,
                            dry_run,
                            show_queries
                        )
                    else:
                        catch_error_and_exit(
                            "iql file must include either 'statecheck' or 'exports' anchor for validation.",
                            self.logger
                        )

                if not is_correct_state and not dry_run:
                    catch_error_and_exit(f"❌ test failed for {resource['name']}.", self.logger)

            #
            # exports with optimization
            #
            if exports_query:
                # OPTIMIZATION: Skip exports if we already ran it as a proxy and have the result
                if exports_result_from_proxy is not None and type in ('resource', 'multi'):
                    self.logger.info(f"📦 reusing exports result from proxy for [{resource['name']}]...")
                    # Process the exports result we already have
                    expected_exports = resource.get('exports', [])
                    if len(expected_exports) > 0:
                        # Use helper method to process the exports data directly
                        self.process_exports_from_result(resource, exports_result_from_proxy, expected_exports)
                else:
                    # Run exports normally
                    self.process_exports(
                        resource, full_context, exports_query, exports_retries,
                        exports_retry_delay, dry_run, show_queries
                    )

            if type == 'resource' and not dry_run:
                self.logger.info(f"✅ test passed for {resource['name']}")

        elapsed_time = datetime.datetime.now() - start_time
        self.logger.info(f"deployment completed in {elapsed_time}")

        # Process stack-level exports if specified
        if output_file:
            self.process_stack_exports(dry_run, output_file)
