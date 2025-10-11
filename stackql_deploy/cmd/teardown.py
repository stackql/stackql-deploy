# cmd/teardown.py
import datetime
from ..lib.utils import (
    catch_error_and_exit,
    get_type,
    print_unicode_box,
    BorderColor
)
from ..lib.config import get_full_context, render_value
from ..lib.templating import get_queries, render_inline_template
from .base import StackQLBase

class StackQLDeProvisioner(StackQLBase):

    def collect_exports(self, show_queries, dry_run):
        self.logger.info(f"collecting exports for [{self.stack_name}] in [{self.stack_env}] environment")

        for resource in self.manifest.get('resources', []):

            type = get_type(resource, self.logger)

            self.logger.info(f"getting exports for resource [{resource['name']}]")

            # get full context
            full_context = get_full_context(self.env, self.global_context, resource, self.logger)

            # get resource queries
            if type != 'command':
                if type == 'query' and 'sql' in resource:
                    # inline SQL specified in the resource
                    test_queries = {}
                    exports_query = render_inline_template(self.env,
                                                            resource["name"],
                                                            resource["sql"],
                                                            full_context,
                                                            self.logger)
                    exports_retries = 1
                    exports_retry_delay = 0
                else:
                    test_queries = get_queries(self.env,
                                                self.stack_dir,
                                                'resources',
                                                resource,
                                                full_context,
                                                self.logger)
                    exports_query = test_queries.get('exports', {}).get('rendered')
                    exports_retries = test_queries.get('exports', {}).get('options', {}).get('retries', 1)
                    exports_retry_delay = test_queries.get('exports', {}).get('options', {}).get('retry_delay', 0)

            if exports_query:
                self.process_exports(
                    resource,
                    full_context,
                    exports_query,
                    exports_retries,
                    exports_retry_delay,
                    dry_run,
                    show_queries,
                    ignore_missing_exports=True
                )

    def run(self, dry_run, show_queries, on_failure):

        start_time = datetime.datetime.now()

        self.logger.info(
            f"tearing down [{self.stack_name}] in [{self.stack_env}] "
            f"environment {'(dry run)' if dry_run else ''}"
        )

        # Collect all exports
        self.collect_exports(show_queries, dry_run)

        for resource in reversed(self.manifest['resources']):

            print_unicode_box(f"Processing resource: [{resource['name']}]", BorderColor.RED)

            # process resources in reverse order
            type = get_type(resource, self.logger)

            if type not in ('resource', 'multi'):
                self.logger.debug(f"skipping resource [{resource['name']}] (type: {type})")
                continue
            else:
                self.logger.info(f"de-provisioning resource [{resource['name']}], type: {type}")

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

            # add reverse export map variable to full context
            if 'exports' in resource:
                for export in resource['exports']:
                    if isinstance(export, dict):
                        for key, lookup_key in export.items():
                            # Get the value from full_context using the lookup_key
                            if lookup_key in full_context:
                                # Add new mapping using the export key and looked up value
                                full_context[key] = full_context[lookup_key]

            #
            # get resource queries
            #
            resource_queries = get_queries(self.env, self.stack_dir, 'resources', resource, full_context, self.logger)

            exists_query = resource_queries.get('exists', {}).get('rendered')
            exists_retries = resource_queries.get('exists', {}).get('options', {}).get('retries', 1)
            exists_retry_delay = resource_queries.get('exists', {}).get('options', {}).get('retry_delay', 0)

            if not exists_query:
                self.logger.info(
                    f"exists query not defined for [{resource['name']}], "
                    f"trying to use statecheck query as exists query."
                )
                exists_query = resource_queries.get('statecheck', {}).get('rendered')
                exists_retries = resource_queries.get('statecheck', {}).get('options', {}).get('retries', 1)
                exists_retry_delay = resource_queries.get('statecheck', {}).get('options', {}).get('retry_delay', 0)
                postdelete_exists_retries = resource_queries.get('statecheck', {}).get(
                    'options', {}
                ).get('postdelete_retries', 10)
                postdelete_exists_retry_delay = resource_queries.get('statecheck', {}).get(
                    'options', {}
                ).get('postdelete_retry_delay', 5)
            else:
                postdelete_exists_retries = resource_queries.get('exists', {}).get(
                    'options', {}
                ).get('postdelete_retries', 10)
                postdelete_exists_retry_delay = resource_queries.get('exists', {}).get(
                    'options', {}
                ).get('postdelete_retry_delay', 5)

            delete_query = resource_queries.get('delete', {}).get('rendered')
            delete_retries = resource_queries.get('delete', {}).get('options', {}).get('retries', 1)
            delete_retry_delay = resource_queries.get('delete', {}).get('options', {}).get('retry_delay', 0)

            if not delete_query:
                self.logger.info(f"delete query not defined for [{resource['name']}], skipping...")
                continue

            #
            # pre-delete check
            #
            ignore_errors = False
            resource_exists = True # assume exists
            if type == 'multi':
                self.logger.info("pre-delete check not supported for multi resources, skipping...")
                ignore_errors  = True # multi resources ignore errors on create or update
            elif type == 'resource':
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

            #
            # delete
            #
            if resource_exists:
                self.delete_resource(
                    resource,
                    full_context,
                    delete_query,
                    delete_retries,
                    delete_retry_delay,
                    dry_run,
                    show_queries,
                    ignore_errors
                )
            else:
                self.logger.info(f"resource [{resource['name']}] does not exist, skipping delete")
                continue

            #
            # confirm deletion
            #
            resource_deleted = self.check_if_resource_exists(
                False,
                resource,
                full_context,
                exists_query,
                postdelete_exists_retries,
                postdelete_exists_retry_delay,
                dry_run,
                show_queries,
                delete_test=True,
            )

            if resource_deleted:
                self.logger.info(f"✅ successfully deleted {resource['name']}")
            else:
                if not dry_run:
                    catch_error_and_exit(f"❌ failed to delete {resource['name']}.", self.logger)

        elapsed_time = datetime.datetime.now() - start_time
        self.logger.info(f"deployment completed in {elapsed_time}")
