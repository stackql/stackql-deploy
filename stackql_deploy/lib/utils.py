import time, json, sys

def catch_error_and_exit(errmsg, logger):
	logger.error(errmsg)
	sys.exit(errmsg)

def run_stackql_query(query, stackql, suppress_errors, logger):
    try:
        logger.debug(f"executing stackql query: {query}")
        result = stackql.execute(query, suppress_errors)
        logger.debug(f"stackql query result: {result}, type: {type(result)}")

        # result should be...
        # [{'error': <error json str>}] if something went wrong; or
        # [{<row1>},...] if the statement was executed successfully, messages to stderr are ignored; or
        # [] if the statement was executed successfully, but no rows were returned

        # result should be a list
        if isinstance(result, list):
            # if suppress_errors is False, we will detect errors where we werent expecting them...
            if not suppress_errors:
                # check if the result contains an error message
                if 'error' in result[0]:
                    error_message = result[0]['error']
                    catch_error_and_exit(f"error occurred during stackql query execution: {error_message}", logger)

            logger.debug(f"stackql query executed successfully, retrieved {len(result)} items.")
            return result
       
        # If result is not a list, it's an unexpected result format
        catch_error_and_exit("unexpected result format received from stackql query execution.", logger)
    
    except Exception as e:
        # Log the exception and exit
        catch_error_and_exit(f"an exception occurred during stackql query execution: {str(e)}", logger)

def run_stackql_command(command, stackql, logger):
    try:
        logger.debug(f"executing stackql command: {command}")
        result = stackql.executeStmt(command)
        logger.debug(f"stackql command result: {result}, type: {type(result)}")

        if isinstance(result, dict):
            # If the result contains a message, it means the execution was successful
            if 'message' in result:
                logger.debug(f"stackql command executed successfully: {result['message']}")
                return result['message']
            elif 'error' in result:
                # Check if the result contains an error message
                error_message = result['error']
                catch_error_and_exit(f"error occurred during stackql command execution: {error_message}", logger)
        
        # If there's no 'error' or 'message', it's an unexpected result format
        catch_error_and_exit("unexpected result format received from stackql execution.", logger)
    
    except Exception as e:
        # Log the exception exit
        catch_error_and_exit(f"an exception occurred during stackql command execution: {str(e)}", logger)

def pull_providers(providers, stackql, logger):
    logger.debug(f"stackql run time info: {json.dumps(stackql.properties(), indent=2)}")
    installed_providers = run_stackql_query("SHOW PROVIDERS", stackql, False, logger) # not expecting an error here
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
        if count != 1:
            logger.debug(f"test result false for [{resource['name']}], expected 1 got {count}.")
            return False
        
        logger.debug(f"test result true for [{resource['name']}]")
        return True

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
