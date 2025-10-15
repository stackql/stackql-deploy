# lib/utils.py
import click
from enum import Enum
import time
import json
import sys
import subprocess
import re

class BorderColor(Enum):
    YELLOW = '\033[93m'  # Bright yellow
    BLUE = '\033[94m'    # Bright blue
    RED = '\033[91m'     # Bright red

def print_unicode_box(message: str, color: BorderColor = BorderColor.YELLOW):
    border_color = color.value
    reset_color = '\033[0m'

    lines = message.split('\n')
    max_length = max(len(line) for line in lines)
    top_border = border_color + '┌' + '─' * (max_length + 2) + '┐' + reset_color
    bottom_border = border_color + '└' + '─' * (max_length + 2) + '┘' + reset_color

    click.echo(top_border)
    for line in lines:
        click.echo(border_color + '│ ' + line.ljust(max_length) + ' │' + reset_color)
    click.echo(bottom_border)

def catch_error_and_exit(errmsg, logger):
    logger.error(errmsg)
    sys.exit("stackql-deploy operation failed 🚫")

def get_type(resource, logger):
    type = resource.get('type', 'resource')
    if type not in ['resource', 'query', 'script', 'multi', 'command']:
        catch_error_and_exit(f"resource type must be 'resource', 'script', 'multi' or 'query', got '{type}'", logger)
    else:
        return type

def run_stackql_query(query, stackql, suppress_errors, logger, custom_auth=None, env_vars=None, retries=0, delay=5):
    attempt = 0
    last_error = None
    while attempt <= retries:
        try:
            logger.debug(f"(utils.run_stackql_query) executing stackql query on attempt {attempt + 1}:\n\n{query}\n")
            result = stackql.execute(query, suppress_errors=suppress_errors, custom_auth=custom_auth, env_vars=env_vars)
            logger.debug(f"(utils.run_stackql_query) stackql query result (type:{type(result)}): {result}")

            # Check if result is a list (expected outcome)
            if isinstance(result, list):
                if len(result) == 0:
                    logger.debug("(utils.run_stackql_query) stackql query executed successfully, retrieved 0 items.")
                    pass
                elif result and 'error' in result[0]:
                    error_message = result[0]['error']
                    last_error = error_message  # Store the error for potential return
                    if not suppress_errors:
                        if attempt == retries:
                            # If retries are exhausted, log the error and exit
                            catch_error_and_exit(
                                (
                                    f"(utils.run_stackql_query) error occurred during stackql query execution:\n\n"
                                    f"{error_message}\n"
                                ),
                                logger
                            )
                        else:
                            # Log the error and prepare for another attempt
                            logger.error(f"attempt {attempt + 1} failed:\n\n{error_message}\n")
                elif 'count' in result[0]:
                    # If the result is a count query, return the count
                    logger.debug(
                        f"(utils.run_stackql_query) stackql query executed successfully, "
                        f"retrieved count: {result[0]['count']}."
                    )
                    if int(result[0]['count']) > 1:
                        catch_error_and_exit(
                            f"(utils.run_stackql_query) detected more than one resource matching the query criteria, "
                            f"expected 0 or 1, got {result[0]['count']}\n",
                            logger
                        )
                    return result
                else:
                    # If no errors or errors are suppressed, return the result
                    logger.debug(
                        f"(utils.run_stackql_query) stackql query executed successfully, retrieved {len(result)} items."
                    )
                    return result
            else:
                # Handle unexpected result format
                if attempt == retries:
                    catch_error_and_exit(
                        "(utils.run_stackql_query) unexpected result format received from stackql query execution.",
                        logger
                    )
                else:
                    logger.error("(utils.run_stackql_query) unexpected result format, retrying...")

        except Exception as e:
            # Log the exception and check if retry attempts are exhausted
            last_error = str(e)  # Store the exception for potential return
            if attempt == retries:
                catch_error_and_exit(
                    f"(utils.run_stackql_query) an exception occurred during stackql query execution:\n\n{str(e)}\n",
                    logger
                )
            else:
                logger.error(f"(utils.run_stackql_query) exception on attempt {attempt + 1}:\n\n{str(e)}\n")

        # Delay before next attempt
        time.sleep(delay)
        attempt += 1

    logger.debug(f"(utils.run_stackql_query) all attempts ({retries + 1}) to execute the query completed.")
    # If suppress_errors is True and we have an error, return an empty list with error info as a special dict
    if suppress_errors and last_error:
        return [{'_stackql_deploy_error': last_error}]
    # return None
    return []

def error_detected(result):
    """parse stdout for known error conditions"""
    if result['message'].startswith('http response status code: 4') or \
       result['message'].startswith('http response status code: 5'):
        return True
    if result['message'].startswith('error:'):
        return True
    if result['message'].startswith('disparity in fields to insert and supplied data'):
        return True
    if result['message'].startswith('cannot find matching operation'):
        return True
    return False

def run_stackql_command(command,
                        stackql,
                        logger,
                        custom_auth=None,
                        env_vars=None,
                        ignore_errors=False,
                        retries=0,
                        retry_delay=5
    ):
    attempt = 0
    while attempt <= retries:
        try:
            logger.debug(
                f"(utils.run_stackql_command) executing stackql command (attempt {attempt + 1}):\n\n{command}\n"
            )
            # If query is start with 'REGISTRY PULL', check version
            if command.startswith("REGISTRY PULL"):
                match = re.match(r'(REGISTRY PULL \w+)(::v[\d\.]+)?', command)
                if match:
                    service_provider = match.group(1)
                    version = match.group(2)
                    if version:
                        command = f"{service_provider} {version[2:]}"
                else:
                    raise ValueError(
                        (
                            "REGISTRY PULL command must be in the format 'REGISTRY PULL <service_provider>::v<version>'"
                            "or 'REGISTRY PULL <service_provider>'"
                        )
                    )

            result = stackql.executeStmt(command, custom_auth, env_vars)
            logger.debug(f"(utils.run_stackql_command) stackql command result:\n\n{result}, type: {type(result)}\n")

            if isinstance(result, dict):
                # If the result contains a message, it means the execution was successful
                if 'message' in result:
                    if not ignore_errors and error_detected(result):
                        if attempt < retries:
                            logger.warning(
                                (
                                    f"dependent resource(s) may not be ready, retrying in {retry_delay} seconds "
                                    f"(attempt {attempt + 1} of {retries + 1})..."
                                )
                            )
                            time.sleep(retry_delay)
                            attempt += 1
                            continue  # Retry the command
                        else:
                            catch_error_and_exit(
                                (
                                    f"(utils.run_stackql_command) error occurred during stackql command execution:\n\n"
                                    f"{result['message']}\n"
                                ),
                                logger
                            )
                    logger.debug(
                        f"(utils.run_stackql_command) stackql command executed successfully:\n\n{result['message']}\n"
                    )
                    return result['message'].rstrip()
                elif 'error' in result:
                    # Check if the result contains an error message
                    error_message = result['error'].rstrip()
                    catch_error_and_exit(
                        (
                            f"(utils.run_stackql_command) error occurred during stackql command execution:\n\n"
                            f"{error_message}\n"
                        ),
                        logger
                    )

            # If there's no 'error' or 'message', it's an unexpected result format
            catch_error_and_exit(
                "(utils.run_stackql_command) unexpected result format received from stackql execution.",
                logger
            )

        except Exception as e:
            # Log the exception and exit
            catch_error_and_exit(
                f"(utils.run_stackql_command) an exception occurred during stackql command execution:\n\n{str(e)}\n",
                logger
            )

        # Increment attempt counter if not continuing the loop due to retry
        attempt += 1

def pull_providers(providers, stackql, logger):
    logger.debug(f"(utils.pull_providers) stackql run time info:\n\n{json.dumps(stackql.properties(), indent=2)}\n")
    installed_providers = run_stackql_query("SHOW PROVIDERS", stackql, False, logger) # not expecting an error here
    # check if the provider is already installed
    for provider in providers:
        # check if the provider is a specific version
        if "::" in provider:
            name, version = provider.split("::")
            check_provider_version_available(name, version, stackql, logger)
            found = False
            # provider is a version which will be installed
            # installed is a version which is already installed
            for installed in installed_providers:
                # if name and version are the same, it's already installed
                if installed["name"] == name and installed["version"] == version:
                    logger.info(f"provider '{provider}' is already installed.")
                    found = True
                    break
                # if name is the same but the installed version is higher,
                # it's already installed(latest version)
                elif installed["name"] == name and is_installed_version_higher(installed["version"], version, logger):
                    logger.warning(
                        (
                            f"provider '{name}' version '{version}' is not available in the registry, "
                            f"but a higher version '{installed['version']}' is already installed."
                        )
                    )
                    logger.warning(
                        "If you want to install the lower version, you must delete the higher version "
                        "folder from the stackql providers directory."
                    )
                    logger.info(f"provider {name}::{version} is already installed.")
                    found = True
                    break
            # if not found, pull the provider
            if not found:
                logger.info(f"pulling provider '{provider}'...")
                msg = run_stackql_command(f"REGISTRY PULL {provider}", stackql, logger)
                logger.info(msg)
        else:
            found = False
            # provider is a name which will be installed
            # installed is a list of providers which are already installed
            for installed in installed_providers:
                if installed["name"] == provider:
                    logger.info(f"provider '{provider}' is already installed.")
                    found = True
                    break
            # if not found, pull the provider
            if not found:
                logger.info(f"pulling provider '{provider}'...")
                msg = run_stackql_command(f"REGISTRY PULL {provider}", stackql, logger)
                logger.info(msg)

def check_provider_version_available(provider_name, version, stackql, logger):
    """Check if the provider version is available in the registry.

    Args:
        provider_name (str): The name of the provider.
        version (str): The version of the provider.
        stackql (StackQL): The StackQL object.
        logger (Logger): The logger object.
    """
    query = f"REGISTRY LIST {provider_name}"
    try:
        result = run_stackql_query(query, stackql, True, logger)
        # result[0]['versions'] is a string, not a list
        # so we need to split it into a list
        versions = result[0]['versions'].split(", ")
        if version not in versions:
            catch_error_and_exit(
                (
                    f"(utils.check_provider_version_available) version '{version}' not found "
                    f"for provider '{provider_name}', available versions: {versions}"
                ),
                logger
            )
    except Exception:
        catch_error_and_exit(
            f"(utils.check_provider_version_available) provider '{provider_name}' not found in registry",
            logger
        )

def is_installed_version_higher(installed_version, requested_version, logger):
    """Check if the installed version is higher than the requested version.

    Args:
        installed_version (str): v24.09.00251
        requested_version (str): v23.01.00104

    Returns:
        bool: True if installed version is higher than requested version, False otherwise
    """

    try:
        int_installed = int(installed_version.replace("v", "").replace(".", ""))
        int_requested = int(requested_version.replace("v", "").replace(".", ""))
        if int_installed > int_requested:
            return True
        else:
            return False
    except Exception:
        catch_error_and_exit(
            (
                f"(utils.is_installed_version_higher) version comparison failed: "
                f"installed version '{installed_version}', requested version '{requested_version}'"
            ),
            logger
        )

def run_test(resource, rendered_test_iql, stackql, logger, delete_test=False, custom_auth=None, env_vars=None):
    try:
        test_result = run_stackql_query(
            rendered_test_iql,
            stackql,
            True,
            logger,
            custom_auth=custom_auth,
            env_vars=env_vars)
        logger.debug(f"(utils.run_test) test query result for [{resource['name']}]:\n\n{test_result}\n")

        if test_result == []:
            if delete_test:
                logger.debug(f"(utils.run_test) delete test result true for [{resource['name']}]")
                return True
            else:
                logger.debug(f"(utils.run_test) test result false for [{resource['name']}]")
                return False

        if not test_result or 'count' not in test_result[0]:
            catch_error_and_exit(
                f"(utils.run_test) data structure unexpected for [{resource['name']}] test:\n\n{test_result}\n", logger
            )

        count = int(test_result[0]['count'])
        if delete_test:
            if count == 0:
                logger.debug(f"(utils.run_test) delete test result true for [{resource['name']}].")
                return True
            else:
                logger.debug(
                    f"(utils.run_test) delete test result false for [{resource['name']}], expected 0 got {count}."
                )
                return False
        else:
            # not a delete test, 1 of the things should exist
            if count == 1:
                logger.debug(f"(utils.run_test) test result true for [{resource['name']}].")
                return True
            else:
                logger.debug(f"(utils.run_test) test result false for [{resource['name']}], expected 1 got {count}.")
                return False

    except Exception as e:
        catch_error_and_exit(
            f"(utils.run_test) an exception occurred during testing for [{resource['name']}]:\n\n{str(e)}\n",
            logger
        )

def show_query(show_queries, query, logger):
    if show_queries:
        logger.info(f"🔍 query:\n\n{query}\n")

def perform_retries(resource,
                    query,
                    retries,
                    delay,
                    stackql,
                    logger,
                    delete_test=False,
                    custom_auth=None,
                    env_vars=None
    ):
    attempt = 0
    start_time = time.time()  # Capture the start time of the operation
    while attempt < retries:
        result = run_test(resource, query, stackql, logger, delete_test, custom_auth=custom_auth, env_vars=env_vars)
        if result:
            return True
        elapsed = time.time() - start_time  # Calculate elapsed time
        logger.info(
            f"🕒 attempt {attempt + 1}/{retries}: retrying in {delay} seconds ({int(elapsed)} seconds elapsed)."
        )
        time.sleep(delay)
        attempt += 1
    elapsed = time.time() - start_time  # Calculate total elapsed time
    return False

def export_vars(self, resource, export, expected_exports, expected_exports_all_dicts, protected_exports):
    for item in expected_exports:
        # check if all items are dictionaries
        if expected_exports_all_dicts:
            if list(item.values())[0] not in export:
                catch_error_and_exit(
                    (
                        f"(utils.export_vars) exported item '{list(item.values())[0]}' "
                        f"not found in exports for {resource['name']}.",
                        self.logger
                    )
                )
        else:
            if item not in export:
                catch_error_and_exit(
                    f"(utils.export_vars) exported item '{item}' not found in exports for {resource['name']}.",
                    self.logger
                )
    for key, value in export.items():
        if key in protected_exports:
            mask = '*' * len(str(value))
            self.logger.info(f"🔒 set protected variable [{key}] to [{mask}] in exports")
        else:
            self.logger.info(f"📤 set [{key}] to [{value}] in exports")
        # Update global context with exported values
        self.global_context[key] = value

def run_ext_script(cmd, logger, exports=None):
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, shell=True)
        logger.debug(f"(utils.run_ext_script) script output: {result.stdout}")
        if not exports:
            return True
    except Exception as e:
        catch_error_and_exit(f"(utils.run_ext_script) script failed: {e}", logger)
        return None

    # we must be expecting exports
    try:
        exported_vars = json.loads(result.stdout)
        # json_output should be a dictionary
        if not isinstance(exported_vars, dict):
            catch_error_and_exit(
                f"(utils.run_ext_script) external scripts must be convertible to a dictionary {exported_vars}",
                logger
            )
            return None
        # you should be able to find each name in exports in the output object
        for export in exports:
            if export not in exported_vars:
                catch_error_and_exit(
                    f"(utils.run_ext_script) exported variable '{export}' not found in script output",
                    logger
                )
                return None
        return exported_vars
    except json.JSONDecodeError:
        catch_error_and_exit(
            f"(utils.run_ext_script) external scripts must return a valid JSON object {result.stdout}",
            logger
        )
        return None

def check_all_dicts(items, logger):
    """ Check if all items(list) are of the same type (either all dicts or all non-dicts).
    """
    all_dicts = all(isinstance(item, dict) for item in items)
    no_dicts = all(not isinstance(item, dict) for item in items)

    if not all_dicts and not no_dicts:
        catch_error_and_exit(f"type inconsistency: all items({items}) must be either dicts or non-dicts", logger)
    if all_dicts:
        return True
    else:
        return False

def check_exports_as_statecheck_proxy(exports_result, logger):
    """
    Check if exports query result can be used as a statecheck proxy.
    Returns True if exports indicate resource is in correct state (non-empty result),
    False if exports indicate statecheck failed (empty result).
    """
    logger.debug(f"(utils.check_exports_as_statecheck_proxy) checking exports result: {exports_result}")

    # If exports is None or empty list, consider statecheck failed
    if exports_result is None or len(exports_result) == 0:
        logger.debug("(utils.check_exports_as_statecheck_proxy) empty exports result, treating as statecheck failure")
        return False

    # Check for error conditions in exports result
    if len(exports_result) >= 1 and isinstance(exports_result[0], dict):
        # Check for our custom error wrapper
        if '_stackql_deploy_error' in exports_result[0]:
            logger.debug(
                "(utils.check_exports_as_statecheck_proxy) error in exports result, "
                "treating as statecheck failure"
            )
            return False
        # Check for direct error in result
        elif 'error' in exports_result[0]:
            logger.debug(
                "(utils.check_exports_as_statecheck_proxy) error in exports result, "
                "treating as statecheck failure"
            )
            return False

    # If we have a valid non-empty result, consider statecheck passed
    logger.debug("(utils.check_exports_as_statecheck_proxy) valid exports result, treating as statecheck success")
    return True
