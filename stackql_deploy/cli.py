import click, os
from dotenv import load_dotenv, dotenv_values
from .lib.bootstrap import logger, stackql
from .cmd.deploy import StackQLProvisioner
from .cmd.test import StackQLTestRunner
from .cmd.teardown import StackQLDeProvisioner

def common_args(f):
    f = click.argument('stack_dir', type=str)(f)
    f = click.argument('environment', type=str)(f)
    return f

def common_options(f):
    f = click.option('--log-level', default='INFO', help='Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')(f)
    f = click.option('--env-file', default='.env', help='Environment variables file.')(f)
    f = click.option('-e', multiple=True, type=(str, str), help='Additional environment variables.')(f)
    f = click.option('--dry-run', is_flag=True, help='Perform a dry run of the stack operation.')(f)
    f = click.option('--on-failure', type=click.Choice(['rollback', 'ignore', 'error']), default='error',
                     help='Action on failure: rollback, ignore or error.')(f)
    return f

def setup_logger(command, args_dict):
    log_level = args_dict.get('log_level', 'INFO')
    logger.setLevel(log_level)
    logger.debug(f"'{command}' command called with args: {str(args_dict)}")

def load_env_vars(env_file, overrides):
    """Load environment variables from a file and apply overrides."""
    # Load environment variables from the specified file into a new dict
    dotenv_path = os.path.join(os.getcwd(), env_file)
    if os.path.exists(dotenv_path):
        env_vars = dict(dotenv_values(dotenv_path))
    else:
        env_vars = {}
    # Apply overrides from the `-e` option
    for key, value in overrides:
        env_vars[key] = value
    return env_vars

@click.command()
@common_args
@common_options
def deploy(environment, stack_dir, log_level, env_file, e, dry_run, on_failure):
    setup_logger("deploy", locals())
    logger.info(f"Deploying {stack_dir} in {environment} {'(dry run)' if dry_run else ''}")
    vars = load_env_vars(env_file, e)
    provisioner = StackQLProvisioner(stackql, vars, logger, stack_dir, environment)
    provisioner.run(dry_run, on_failure)

@click.command()
@common_args
@common_options
def teardown(environment, stack_dir, log_level, env_file, e, dry_run, on_failure):
    setup_logger("teardown", locals())
    logger.info(f"Tearing down {stack_dir} in {environment} {'(dry run)' if dry_run else ''}")
    vars = load_env_vars(env_file, e)
    deprovisioner = StackQLDeProvisioner(stackql, vars, logger, stack_dir, environment)
    deprovisioner.run(dry_run, on_failure)

@click.command()
@common_args
@common_options
def test(environment, stack_dir, log_level, env_file, e, dry_run, on_failure):
    setup_logger("test", locals())
    logger.info(f"Testing {stack_dir} in {environment} {'(dry run)' if dry_run else ''}")
    vars = load_env_vars(env_file, e)
    test_runner = StackQLTestRunner(stackql, vars, logger, stack_dir, environment)
    test_runner.run(dry_run, on_failure)

@click.group()
def cli():
    pass

cli.add_command(deploy)
cli.add_command(test)
cli.add_command(teardown)

if __name__ == '__main__':
    cli()
