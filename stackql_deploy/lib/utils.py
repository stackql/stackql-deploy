import time, json, sys, subprocess

def catch_error_and_exit(errmsg, logger):
	logger.error(errmsg)
	sys.exit(errmsg)

def get_type(resource, logger):
    type = resource.get('type', 'resource')
    if type not in ['resource', 'query', 'script']:
        catch_error_and_exit(f"resource type must be 'resource', 'script' or 'query', got '{type}'", logger)
    else:
        return type

def run_stackql_query(query, stackql, suppress_errors, logger, retries=0, delay=5):
    attempt = 0
    while attempt <= retries:
        try:
            logger.debug(f"(utils.run_stackql_query) executing stackql query on attempt {attempt + 1}:\n\n{query}\n")
            result = stackql.execute(query, suppress_errors)
            logger.debug(f"(utils.run_stackql_query) stackql query result (type:{type(result)}): {result}")

            # Check if result is a list (expected outcome)
            if isinstance(result, list):
                if len(result) == 0:
                    logger.debug("(utils.run_stackql_query) stackql query executed successfully, retrieved 0 items.")
                    pass
                elif not suppress_errors and result and 'error' in result[0]:
                    error_message = result[0]['error']
                    if attempt == retries:
                        # If retries are exhausted, log the error and exit
                        catch_error_and_exit(f"(utils.run_stackql_query) error occurred during stackql query execution:\n\n{error_message}\n", logger)
                    else:
                        # Log the error and prepare for another attempt
                        logger.error(f"attempt {attempt + 1} failed:\n\n{error_message}\n")
                elif 'count' in result[0]:
                    # If the result is a count query, return the count
                    logger.debug(f"(utils.run_stackql_query) stackql query executed successfully, retrieved count: {result[0]['count']}.")
                    if int(result[0]['count']) > 1:
                        catch_error_and_exit(f"(utils.run_stackql_query) detected more than one resource matching the query criteria, expected 0 or 1, got {result[0]['count']}\n", logger)
                    return result
                else:
                    # If no errors or errors are suppressed, return the result
                    logger.debug(f"(utils.run_stackql_query) stackql query executed successfully, retrieved {len(result)} items.")
                    return result
            else:
                # Handle unexpected result format
                if attempt == retries:
                    catch_error_and_exit("(utils.run_stackql_query) unexpected result format received from stackql query execution.", logger)
                else:
                    logger.error("(utils.run_stackql_query) unexpected result format, retrying...")

        except Exception as e:
            # Log the exception and check if retry attempts are exhausted
            if attempt == retries:
                catch_error_and_exit(f"(utils.run_stackql_query) an exception occurred during stackql query execution:\n\n{str(e)}\n", logger)
            else:
                logger.error(f"(utils.run_stackql_query) exception on attempt {attempt + 1}:\n\n{str(e)}\n")

        # Delay before next attempt
        time.sleep(delay)
        attempt += 1

    logger.debug(f"(utils.run_stackql_query) all attempts ({retries + 1}) to execute the query completed.")
    # return None
    return []

def error_detected(result):
    """parse stdout for known error conditions"""
    # aws cloud control hack...
    if result['message'].startswith('http response status code: 4') or result['message'].startswith('http response status code: 5'):
        return True
    if result['message'].startswith('error:'):
        return True
    if result['message'].startswith('disparity in fields to insert and supplied data'):
        return True
    if result['message'].startswith('cannot find matching operation'):
        return True    
    return False
        
def run_stackql_command(command, stackql, logger):
    try:
        logger.debug(f"(utils.run_stackql_command) executing stackql command:\n\n{command}\n")
        result = stackql.executeStmt(command)
        logger.debug(f"(utils.run_stackql_command) stackql command result:\n\n{result}, type: {type(result)}\n")

        if isinstance(result, dict):
            # If the result contains a message, it means the execution was successful
            if 'message' in result:
                if error_detected(result):
                    catch_error_and_exit(f"(utils.run_stackql_command) error occurred during stackql command execution:\n\n{result['message']}\n", logger)
                logger.debug(f"(utils.run_stackql_command) stackql command executed successfully:\n\n{result['message']}\n")
                return result['message'].rstrip()
            elif 'error' in result:
                # Check if the result contains an error message
                error_message = result['error'].rstrip()
                catch_error_and_exit(f"(utils.run_stackql_command) error occurred during stackql command execution:\n\n{error_message}\n", logger)
        
        # If there's no 'error' or 'message', it's an unexpected result format
        catch_error_and_exit("(utils.run_stackql_command) unexpected result format received from stackql execution.", logger)
    
    except Exception as e:
        # Log the exception exit
        catch_error_and_exit(f"(utils.run_stackql_command) an exception occurred during stackql command execution:\n\n{str(e)}\n", logger)

def pull_providers(providers, stackql, logger):
    logger.debug(f"(utils.pull_providers) stackql run time info:\n\n{json.dumps(stackql.properties(), indent=2)}\n")
    installed_providers = run_stackql_query("SHOW PROVIDERS", stackql, False, logger) # not expecting an error here
    if len(installed_providers) == 0:
        installed_names = set()
    else:
        installed_names = {provider["name"] for provider in installed_providers}
    for provider in providers:
        if provider not in installed_names:
            logger.info(f"pulling provider '{provider}'...")
            msg = run_stackql_command(f"REGISTRY PULL {provider}", stackql, logger)
            logger.info(msg)
        else:
            logger.info(f"provider '{provider}' is already installed.")

def run_test(resource, rendered_test_iql, stackql, logger, delete_test=False):
    try:
        test_result = run_stackql_query(rendered_test_iql, stackql, True, logger)
        logger.debug(f"(utils.run_test) test query result for [{resource['name']}]:\n\n{test_result}\n")

        if test_result == []:
            if delete_test:
                logger.debug(f"(utils.run_test) delete test result true for [{resource['name']}]")
                return True
            else:
                logger.debug(f"(utils.run_test) test result false for [{resource['name']}]")
                return False

        if not test_result or 'count' not in test_result[0]:
            catch_error_and_exit(f"(utils.run_test) data structure unexpected for [{resource['name']}] test:\n\n{test_result}\n", logger)
        
        count = int(test_result[0]['count'])
        if delete_test:
            if count == 0:
                logger.debug(f"(utils.run_test) delete test result true for [{resource['name']}].")
                return True
            else:
                logger.debug(f"(utils.run_test) delete test result false for [{resource['name']}], expected 0 got {count}.")
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
        catch_error_and_exit(f"(utils.run_test) an exception occurred during testing for [{resource['name']}]:\n\n{str(e)}\n", logger)

def show_query(show_queries, query, logger):
    if show_queries:
        logger.info(f"🔍 query:\n\n{query}\n")

def perform_retries(resource, query, retries, delay, stackql, logger, delete_test=False):
    attempt = 0
    start_time = time.time()  # Capture the start time of the operation
    while attempt < retries:
        result = run_test(resource, query, stackql, logger, delete_test)
        if result:
            return True
        elapsed = time.time() - start_time  # Calculate elapsed time
        logger.info(f"🕒 attempt {attempt + 1}/{retries}: retrying in {delay} seconds ({int(elapsed)} seconds elapsed).")
        time.sleep(delay)
        attempt += 1
    elapsed = time.time() - start_time  # Calculate total elapsed time
    return False

def export_vars(self, resource, export, expected_exports, protected_exports):
    for key in expected_exports:
        if key not in export:
            catch_error_and_exit(f"(utils.export_vars) exported key '{key}' not found in exports for {resource['name']}.", self.logger)

    for key, value in export.items():
        if key in protected_exports:
            mask = '*' * len(str(value))
            self.logger.info(f"🔒  set protected variable [{key}] to [{mask}] in exports")
        else:
            self.logger.info(f"➡️  set [{key}] to [{value}] in exports")

        self.global_context[key] = value  # Update global context with exported values

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
            catch_error_and_exit(f"(utils.run_ext_script) external scripts must be convertible to a dictionary {exported_vars}", logger)
            return None
        # you should be able to find each name in exports in the output object
        for export in exports:
            if export not in exported_vars:
                catch_error_and_exit(f"(utils.run_ext_script) exported variable '{export}' not found in script output", logger)
                return None
        return exported_vars
    except json.JSONDecodeError:
        catch_error_and_exit(f"(utils.run_ext_script) external scripts must return a valid JSON object {result.stdout}", logger)
        return None