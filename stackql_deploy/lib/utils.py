import time, json, sys

def catch_error_and_exit(errmsg, logger):
	logger.error(errmsg)
	sys.exit(errmsg)


def run_stackql_query(query, stackql, suppress_errors, logger, retries=0, delay=5):
    attempt = 0
    while attempt <= retries:
        try:
            logger.debug(f"Executing stackql query on attempt {attempt + 1}: {query}")
            result = stackql.execute(query, suppress_errors)
            logger.debug(f"StackQL query result: {result}, type: {type(result)}")

            # Check if result is a list (expected outcome)
            if isinstance(result, list):
                if not suppress_errors and result and 'error' in result[0]:
                    error_message = result[0]['error']
                    if attempt == retries:
                        # If retries are exhausted, log the error and exit
                        catch_error_and_exit(f"Error occurred during stackql query execution: {error_message}", logger)
                    else:
                        # Log the error and prepare for another attempt
                        logger.error(f"Attempt {attempt + 1} failed: {error_message}")
                else:
                    # If no errors or errors are suppressed, return the result
                    logger.debug(f"StackQL query executed successfully, retrieved {len(result)} items.")
                    return result

            else:
                # Handle unexpected result format
                if attempt == retries:
                    catch_error_and_exit("Unexpected result format received from stackql query execution.", logger)
                else:
                    logger.error("Unexpected result format, retrying...")

        except Exception as e:
            # Log the exception and check if retry attempts are exhausted
            if attempt == retries:
                catch_error_and_exit(f"An exception occurred during stackql query execution: {str(e)}", logger)
            else:
                logger.error(f"Exception on attempt {attempt + 1}: {str(e)}")

        # Delay before next attempt
        time.sleep(delay)
        attempt += 1

    # If all attempts fail and no result is returned, log the final failure
    logger.error(f"All attempts ({retries + 1}) to execute the query failed.")
    return None

def run_stackql_command(command, stackql, logger):
    try:
        logger.debug(f"executing stackql command: {command}")
        result = stackql.executeStmt(command)
        logger.debug(f"stackql command result: {result}, type: {type(result)}")

        if isinstance(result, dict):
            # If the result contains a message, it means the execution was successful
            if 'message' in result:
                logger.debug(f"stackql command executed successfully: {result['message']}")
                return result['message'].rstrip()
            elif 'error' in result:
                # Check if the result contains an error message
                error_message = result['error'].rstrip()
                catch_error_and_exit(f"error occurred during stackql command execution: {error_message}", logger)
        
        # If there's no 'error' or 'message', it's an unexpected result format
        catch_error_and_exit("unexpected result format received from stackql execution.", logger)
    
    except Exception as e:
        # Log the exception exit
        catch_error_and_exit(f"an exception occurred during stackql command execution: {str(e)}", logger)

def pull_providers(providers, stackql, logger):
    logger.debug(f"stackql run time info: {json.dumps(stackql.properties(), indent=2)}")
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
        logger.debug(f"test query result for [{resource['name']}]: {test_result}")

        if test_result == []:
            if delete_test:
                logger.debug(f"delete test result true for [{resource['name']}]")
                return True
            else:
                logger.debug(f"test result false for [{resource['name']}]")
                return False

        if not test_result or 'count' not in test_result[0]:
            catch_error_and_exit(f"test data structure unexpected for [{resource['name']}]: {test_result}", logger)
        
        count = int(test_result[0]['count'])
        if delete_test:
            if count == 0:
                logger.debug(f"delete test result true for [{resource['name']}].")
                return True
            else:
                logger.debug(f"delete test result false for [{resource['name']}], expected 0 got {count}.")
                return False
        else:
            # not a delete test, 1 of the things should exist
            if count == 1:
                logger.debug(f"test result true for [{resource['name']}].")
                return True
            else:
                logger.debug(f"test result false for [{resource['name']}], expected 1 got {count}.")
                return False

    except Exception as e:
        catch_error_and_exit(f"an exception occurred during testing for [{resource['name']}]: {str(e)}", logger)

def perform_retries(resource, query, retries, delay, stackql, logger, delete_test=False):
    attempt = 0
    start_time = time.time()  # Capture the start time of the operation
    while attempt < retries:
        result = run_test(resource, query, stackql, logger, delete_test)
        if result:
            return True
        elapsed = time.time() - start_time  # Calculate elapsed time
        logger.info(f"attempt {attempt + 1}/{retries}: retrying in {delay} seconds ({int(elapsed)} seconds elapsed).")
        time.sleep(delay)
        attempt += 1
    elapsed = time.time() - start_time  # Calculate total elapsed time
    logger.error(f"failed after {retries} retries in {int(elapsed)} seconds.")
    return False
