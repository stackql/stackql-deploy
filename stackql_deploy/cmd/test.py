# cmd/test.py
import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, Tuple

from ..lib.utils import (
    catch_error_and_exit,
    get_type,
    print_unicode_box,
    BorderColor
)
from ..lib.config import get_full_context
from ..lib.templating import get_queries, render_inline_template
from .base import StackQLBase


class ResourceType(Enum):
    """Resource types supported by StackQL test runner."""
    RESOURCE = 'resource'
    MULTI = 'multi'
    QUERY = 'query'
    COMMAND = 'command'
    SCRIPT = 'script'


@dataclass
class QueryConfig:
    """Configuration for a query execution."""
    query: Optional[str]
    retries: int = 1
    retry_delay: int = 0


@dataclass
class TestQueries:
    """Container for test-related queries."""
    statecheck: QueryConfig
    exports: QueryConfig


class StackQLTestRunner(StackQLBase):

    def _extract_query_config(self, resource_queries: Dict, query_type: str) -> QueryConfig:
        """Extract query configuration from resource_queries."""
        query_data = resource_queries.get(query_type, {})
        return QueryConfig(
            query=query_data.get('rendered'),
            retries=query_data.get('options', {}).get('retries', 1),
            retry_delay=query_data.get('options', {}).get('retry_delay', 0)
        )

    def _get_resource_queries(
        self,
        resource: Dict,
        resource_type: str,
        full_context: Dict
    ) -> Tuple[Dict, Optional[str]]:
        """Get resource queries, handling both inline SQL and file-based queries."""
        inline_query = None

        if resource_type == ResourceType.QUERY.value and 'sql' in resource:
            # Inline SQL specified in the resource
            inline_query = render_inline_template(
                self.env,
                resource["name"],
                resource["sql"],
                full_context,
                self.logger
            )
            return {}, inline_query

        # Load queries from file
        resource_queries = get_queries(
            self.env,
            self.stack_dir,
            'resources',
            resource,
            full_context,
            self.logger
        )
        return resource_queries, inline_query

    def _build_test_queries(
        self,
        resource_queries: Dict,
        resource_type: str,
        inline_query: Optional[str]
    ) -> TestQueries:
        """Build all test queries from resource_queries."""
        statecheck = self._extract_query_config(resource_queries, 'statecheck')
        exports = self._extract_query_config(resource_queries, 'exports')

        # Handle inline query for query type resources
        if resource_type == ResourceType.QUERY.value and not exports.query:
            if inline_query:
                exports = QueryConfig(query=inline_query, retries=1, retry_delay=0)

        return TestQueries(statecheck=statecheck, exports=exports)

    def _validate_query_resource(
        self,
        resource: Dict,
        queries: TestQueries
    ):
        """Validate that query type resources have required exports."""
        if not queries.exports.query:
            catch_error_and_exit(
                "inline sql must be supplied or an iql file must be present with an "
                "'exports' anchor for query type resources.",
                self.logger
            )

    def _perform_state_check(
        self,
        resource: Dict,
        full_context: Dict,
        queries: TestQueries,
        dry_run: bool,
        show_queries: bool
    ) -> Tuple[bool, Optional[Any]]:
        """Perform state check for resource, returning (is_correct_state, exports_result)."""
        if resource.get('skip_validation', False):
            self.logger.info(f"Skipping statecheck for {resource['name']}")
            return True, None

        if queries.statecheck.query:
            is_correct_state = self.check_if_resource_is_correct_state(
                False,
                resource,
                full_context,
                queries.statecheck.query,
                queries.statecheck.retries,
                queries.statecheck.retry_delay,
                dry_run,
                show_queries
            )
            return is_correct_state, None

        elif queries.exports.query:
            # OPTIMIZATION: Use exports as statecheck proxy for test
            self.logger.info(
                f"🔄 using exports query as proxy for statecheck test "
                f"for [{resource['name']}]"
            )
            is_correct_state, exports_result = self.check_state_using_exports_proxy(
                resource,
                full_context,
                queries.exports.query,
                queries.exports.retries,
                queries.exports.retry_delay,
                dry_run,
                show_queries
            )
            return is_correct_state, exports_result

        else:
            catch_error_and_exit(
                "iql file must include either 'statecheck' or 'exports' anchor for validation.",
                self.logger
            )

    def _handle_exports(
        self,
        resource: Dict,
        full_context: Dict,
        queries: TestQueries,
        exports_result_from_proxy: Optional[Any],
        resource_type: str,
        dry_run: bool,
        show_queries: bool
    ):
        """Handle exports for resources."""
        if not queries.exports.query:
            return

        # OPTIMIZATION: Skip exports if we already ran it as a proxy and have the result
        if (exports_result_from_proxy is not None
            and resource_type in (ResourceType.RESOURCE.value, ResourceType.MULTI.value)):
            self.logger.info(f"📦 reusing exports result from proxy for [{resource['name']}]...")
            expected_exports = resource.get('exports', [])
            if len(expected_exports) > 0:
                self.process_exports_from_result(
                    resource, exports_result_from_proxy, expected_exports
                )
        else:
            # Run exports normally
            self.process_exports(
                resource,
                full_context,
                queries.exports.query,
                queries.exports.retries,
                queries.exports.retry_delay,
                dry_run,
                show_queries
            )

    def _process_resource(
        self,
        resource: Dict,
        dry_run: bool,
        show_queries: bool
    ):
        """Process a single resource."""
        print_unicode_box(f"Processing resource: [{resource['name']}]", BorderColor.BLUE)

        resource_type = get_type(resource, self.logger)

        # Log what we're doing
        if resource_type == ResourceType.QUERY.value:
            self.logger.info(f"exporting variables for [{resource['name']}]")
        elif resource_type in (ResourceType.RESOURCE.value, ResourceType.MULTI.value):
            self.logger.info(f"testing resource [{resource['name']}], type: {resource_type}")
        elif resource_type == ResourceType.COMMAND.value:
            return  # Skip command resources
        else:
            catch_error_and_exit(f"unknown resource type: {resource_type}", self.logger)

        # Get full context
        full_context = get_full_context(self.env, self.global_context, resource, self.logger)

        # Get resource queries
        resource_queries, inline_query = self._get_resource_queries(
            resource, resource_type, full_context
        )

        # Build test queries
        queries = self._build_test_queries(resource_queries, resource_type, inline_query)

        # Validate query resources
        if resource_type == ResourceType.QUERY.value:
            self._validate_query_resource(resource, queries)

        # Perform state check for resource/multi types
        exports_result_from_proxy = None
        if resource_type in (ResourceType.RESOURCE.value, ResourceType.MULTI.value):
            is_correct_state, exports_result_from_proxy = self._perform_state_check(
                resource, full_context, queries, dry_run, show_queries
            )

            if not is_correct_state and not dry_run:
                catch_error_and_exit(f"❌ test failed for {resource['name']}.", self.logger)

        # Handle exports
        self._handle_exports(
            resource, full_context, queries, exports_result_from_proxy,
            resource_type, dry_run, show_queries
        )

        # Log success
        if resource_type == ResourceType.RESOURCE.value and not dry_run:
            self.logger.info(f"✅ test passed for {resource['name']}")

    def run(self, dry_run, show_queries, on_failure, output_file=None):
        """Run the test process for all resources."""
        start_time = datetime.datetime.now()

        self.logger.info(
            f"testing [{self.stack_name}] in [{self.stack_env}] environment "
            f"{'(dry run)' if dry_run else ''}"
        )

        for resource in self.manifest.get('resources', []):
            self._process_resource(resource, dry_run, show_queries)

        elapsed_time = datetime.datetime.now() - start_time
        self.logger.info(f"deployment completed in {elapsed_time}")

        # Process stack-level exports if specified
        if output_file:
            self.process_stack_exports(dry_run, output_file, elapsed_time)
