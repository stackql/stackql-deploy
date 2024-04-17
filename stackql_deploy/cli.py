import click, os
from . import __version__ as deploy_version
from dotenv import load_dotenv, dotenv_values
from .lib.bootstrap import logger, stackql
from .cmd.build import StackQLProvisioner
from .cmd.test import StackQLTestRunner
from .cmd.teardown import StackQLDeProvisioner
from jinja2 import Environment, FileSystemLoader

def common_args(f):
    f = click.argument('stack_env', type=str)(f)
    f = click.argument('stack_dir', type=str)(f)
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
def build(stack_dir, stack_env, log_level, env_file, e, dry_run, on_failure):
    """Create or update resources to a desired state in a stack defined in the `{STACK_DIR}/stackql_manifest.yml` file."""
    setup_logger("build", locals())
    vars = load_env_vars(env_file, e)
    provisioner = StackQLProvisioner(stackql, vars, logger, stack_dir, stack_env)
    provisioner.run(dry_run, on_failure)

@click.command()
@common_args
@common_options
def teardown(stack_dir, stack_env, log_level, env_file, e, dry_run, on_failure):
    """Teardown a provisioned stack defined in the `{STACK_DIR}/stackql_manifest.yml` file."""
    setup_logger("teardown", locals())
    vars = load_env_vars(env_file, e)
    deprovisioner = StackQLDeProvisioner(stackql, vars, logger, stack_dir, stack_env)
    deprovisioner.run(dry_run, on_failure)

@click.command()
@common_args
@common_options
def test(stack_dir, stack_env, log_level, env_file, e, dry_run, on_failure):
    """Run test queries to ensure desired state resources and configuration for the stack defined in the `{STACK_DIR}/stackql_manifest.yml` file."""
    setup_logger("test", locals())
    vars = load_env_vars(env_file, e)
    test_runner = StackQLTestRunner(stackql, vars, logger, stack_dir, stack_env)
    test_runner.run(dry_run, on_failure)

@click.command()
def info():
    """Display the version information of stackql-deploy and stackql library."""
    max_label_length = max(len(label) for label, _ in [
        ("stackql-deploy version", ""),
        ("pystackql version", ""),
        ("stackql version", ""),
        ("stackql binary path", ""),
        ("platform", "")
    ])
    info_items = [
        ("stackql-deploy version", deploy_version),
        ("pystackql version", stackql.package_version),
        ("stackql version", stackql.version),
        ("stackql binary path", stackql.bin_path),
        ("platform", stackql.platform)
    ]
    for label, value in info_items:
        click.echo(f"{label.ljust(max_label_length)}: {value}")

def create_project_structure(stack_name):
    base_path = os.path.join(os.getcwd(), stack_name)
    if os.path.exists(base_path):
        raise click.ClickException(f"Directory '{stack_name}' already exists.")
    
    directories = ['stackql_docs', 'stackql_resources', 'stackql_tests']
    for directory in directories:
        os.makedirs(os.path.join(base_path, directory), exist_ok=True)
    
    template_base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    env = Environment(loader=FileSystemLoader(template_base_path))

    logger.debug(f"template base path: {template_base_path}")

    template_files = {
        'stackql_manifest.yml.template': os.path.join(base_path, 'stackql_manifest.yml'),
        'stackql_docs/stackql_example_rg.md.template': os.path.join(base_path,'stackql_docs', 'stackql_example_rg.md'),
        'stackql_resources/stackql_example_rg.iql.template': os.path.join(base_path,'stackql_resources', 'stackql_example_rg.iql'),
        'stackql_tests/stackql_example_rg.iql.template': os.path.join(base_path,'stackql_tests', 'stackql_example_rg.iql')
    }
    
    for template_name, output_name in template_files.items():
        logger.debug(f"template name: {template_name}")
        logger.debug(f"template output name: {output_name}")
        template = env.get_template(template_name)
        rendered_content = template.render(stack_name=stack_name)
        with open(os.path.join(base_path, output_name), 'w') as f:
            f.write(rendered_content)


@click.command()
@click.argument('stack_name')
@click.option('--log-level', default='INFO', help='Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
def init(stack_name, log_level):
    """Initialize a new stackql-deploy project structure."""
    setup_logger("init", locals())
    create_project_structure(stack_name)
    click.echo(f"project {stack_name} initialized successfully.")

@click.group()
def cli():
    pass

cli.add_command(build)
cli.add_command(test)
cli.add_command(teardown)
cli.add_command(info)
cli.add_command(init)

if __name__ == '__main__':
    cli()
