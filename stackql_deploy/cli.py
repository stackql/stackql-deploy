import click, os
from . import __version__ as deploy_version
from .lib.bootstrap import logger
from .cmd.build import StackQLProvisioner
from .cmd.test import StackQLTestRunner
from .cmd.teardown import StackQLDeProvisioner
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv, dotenv_values
from pystackql import StackQL

def get_stackql_instance(custom_registry=None, download_dir=None):
    """Initializes StackQL with the given options."""
    stackql_kwargs = {}
    if custom_registry:
        stackql_kwargs['custom_registry'] = custom_registry
    if download_dir:
        stackql_kwargs['download_dir'] = download_dir

    return StackQL(**stackql_kwargs)

def load_env_vars(env_file, overrides):
    """Load environment variables from a file and apply overrides."""
    dotenv_path = os.path.join(os.getcwd(), env_file)
    env_vars = {}

    # Load environment variables from the specified file into a new dict
    if os.path.exists(dotenv_path):
        env_vars.update(dotenv_values(dotenv_path))  # Use update to load the .env file

    # Apply overrides from the `-e` option
    env_vars.update(overrides)  # Directly update the dictionary with another dictionary

    return env_vars

def parse_env_var(ctx, param, value):
    """Parse environment variable options given as 'KEY=VALUE'."""
    env_vars = {}
    if value:
        for item in value:
            try:
                key, val = item.split('=', 1)
                env_vars[key] = val
            except ValueError:
                raise click.BadParameter('Environment variables must be formatted as KEY=VALUE')
    return env_vars

def setup_logger(command, args_dict):
    log_level = args_dict.get('log_level', 'INFO')
    logger.setLevel(log_level)
    logger.debug(f"'{command}' command called with args: {str(args_dict)}")

#
# main entry point
#

@click.group()
@click.option('--custom-registry', default=None, help='Custom registry URL for StackQL.')
@click.option('--download-dir', default=None, help='Download directory for StackQL.')
@click.pass_context
def cli(ctx, custom_registry, download_dir):
    """This is the main CLI entry point."""
    ctx.ensure_object(dict)
    ctx.obj['custom_registry'] = custom_registry
    ctx.obj['download_dir'] = download_dir


#
# build command
#

@cli.command()
@click.argument('stack_dir')
@click.argument('stack_env')
@click.option('--log-level', default='INFO', help='Set the logging level.')
@click.option('--env-file', default='.env', help='Environment variables file.')
@click.option('-e', '--env', multiple=True, callback=parse_env_var, help='Set additional environment variables.')
@click.option('--dry-run', is_flag=True, help='Perform a dry run of the operation.')
@click.option('--on-failure', type=click.Choice(['rollback', 'ignore', 'error']), default='error', help='Action on failure.')
@click.pass_context
def build(ctx, stack_dir, stack_env, log_level, env_file, env, dry_run, on_failure):
    """Create or update resources."""
    setup_logger(log_level, locals())
    env_vars = load_env_vars(env_file, env)
    stackql = get_stackql_instance(ctx.obj['custom_registry'], ctx.obj['download_dir'])
    provisioner = StackQLProvisioner(stackql, env_vars, logger, stack_dir, stack_env)
    provisioner.run(dry_run, on_failure)
    click.echo(f"🚀 build complete (dry run: {dry_run})")

#
# teardown command
#

@cli.command()
@click.argument('stack_dir')
@click.argument('stack_env')
@click.option('--log-level', default='INFO', help='Set the logging level.')
@click.option('--env-file', default='.env', help='Environment variables file.')
@click.option('-e', '--env', multiple=True, callback=parse_env_var, help='Set additional environment variables.')
@click.option('--dry-run', is_flag=True, help='Perform a dry run of the operation.')
@click.option('--on-failure', type=click.Choice(['rollback', 'ignore', 'error']), default='error', help='Action on failure.')
@click.pass_context
def teardown(ctx, stack_dir, stack_env, log_level, env_file, env, dry_run, on_failure):
    """Teardown a provisioned stack defined in the `{STACK_DIR}/stackql_manifest.yml` file."""
    setup_logger("teardown", locals())
    stackql = get_stackql_instance(
        custom_registry=ctx.obj.get('custom_registry'), 
        download_dir=ctx.obj.get('download_dir')
    )
    vars = load_env_vars(env_file, env)
    deprovisioner = StackQLDeProvisioner(stackql, vars, logger, stack_dir, stack_env)
    deprovisioner.run(dry_run, on_failure)
    click.echo(f"🚧 teardown complete (dry run: {dry_run})")

#
# test command
#

@cli.command()
@click.argument('stack_dir')
@click.argument('stack_env')
@click.option('--log-level', default='INFO', help='Set the logging level.')
@click.option('--env-file', default='.env', help='Environment variables file.')
@click.option('-e', '--env', multiple=True, callback=parse_env_var, help='Set additional environment variables.')
@click.option('--dry-run', is_flag=True, help='Perform a dry run of the operation.')
@click.option('--on-failure', type=click.Choice(['rollback', 'ignore', 'error']), default='error', help='Action on failure.')
@click.pass_context
def test(ctx, stack_dir, stack_env, log_level, env_file, env, dry_run, on_failure):
    """Run test queries to ensure desired state resources and configuration for the stack defined in the `{STACK_DIR}/stackql_manifest.yml` file."""
    setup_logger("test", locals())
    stackql = get_stackql_instance(
        custom_registry=ctx.obj.get('custom_registry'), 
        download_dir=ctx.obj.get('download_dir')
    )
    vars = load_env_vars(env_file, env)
    test_runner = StackQLTestRunner(stackql, vars, logger, stack_dir, stack_env)
    test_runner.run(dry_run, on_failure)
    click.echo(f"🔍 tests complete (dry run: {dry_run})")

#
# info command
#

# stackql-deploy --custom-registry="https://registry-dev.stackql.app/providers" --download-dir . info
@cli.command()
@click.pass_context
def info(ctx):
    """Display the version information of stackql-deploy and stackql library."""
    # Get an instance of StackQL with current context options
    stackql = get_stackql_instance(
        custom_registry=ctx.obj.get('custom_registry'),
        download_dir=ctx.obj.get('download_dir')
    )
    
    # Prepare information items to display, including conditional custom registry
    info_items = [
        ("stackql-deploy version", deploy_version),
        ("pystackql version", stackql.package_version),
        ("stackql version", stackql.version),
        ("stackql binary path", stackql.bin_path),
        ("platform", stackql.platform),
    ]
    
    # Optionally add custom registry if it's provided
    if ctx.obj.get('custom_registry'):
        info_items.append(("custom registry", ctx.obj.get('custom_registry')))
    
    # Calculate the maximum label length for alignment
    max_label_length = max(len(label) for label, _ in info_items)
    
    # Print out all information items
    for label, value in info_items:
        click.echo(f"{label.ljust(max_label_length)}: {value}")

#
# init command
#

def create_project_structure(stack_name):
    base_path = os.path.join(os.getcwd(), stack_name)
    if os.path.exists(base_path):
        raise click.ClickException(f"Directory '{stack_name}' already exists.")
    
    directories = ['stackql_docs', 'stackql_resources', 'stackql_queries']
    for directory in directories:
        os.makedirs(os.path.join(base_path, directory), exist_ok=True)
    
    template_base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    env = Environment(loader=FileSystemLoader(template_base_path))

    logger.debug(f"template base path: {template_base_path}")

    template_files = {
        'stackql_manifest.yml.template': os.path.join(base_path, 'stackql_manifest.yml'),
        'stackql_docs/stackql_example_rg.md.template': os.path.join(base_path,'stackql_docs', 'stackql_example_rg.md'),
        'stackql_resources/stackql_example_rg.iql.template': os.path.join(base_path,'stackql_resources', 'stackql_example_rg.iql'),
        'stackql_queries/stackql_example_rg.iql.template': os.path.join(base_path,'stackql_queries', 'stackql_example_rg.iql')
    }
    
    for template_name, output_name in template_files.items():
        logger.debug(f"template name: {template_name}")
        logger.debug(f"template output name: {output_name}")
        template = env.get_template(template_name)
        rendered_content = template.render(stack_name=stack_name)
        with open(os.path.join(base_path, output_name), 'w') as f:
            f.write(rendered_content)

@cli.command()
@click.argument('stack_name')
def init(stack_name):
    """Initialize a new stackql-deploy project structure."""
    setup_logger("init", locals())
    create_project_structure(stack_name)
    click.echo(f"project {stack_name} initialized successfully.")


cli.add_command(build)
cli.add_command(test)
cli.add_command(teardown)
cli.add_command(info)
cli.add_command(init)

if __name__ == '__main__':
    cli()