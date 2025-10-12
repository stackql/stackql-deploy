# cli.py
import click
import os
import sys
import subprocess

from . import __version__ as deploy_version

from .lib.bootstrap import logger
from .lib.utils import print_unicode_box, BorderColor
# from .cmd.build import StackQLProvisioner
# from .cmd.test import StackQLTestRunner
# from .cmd.teardown import StackQLDeProvisioner
from jinja2 import Environment, FileSystemLoader
from dotenv import dotenv_values
from pystackql import StackQL

#
# utility functions
#

def get_stackql_instance(custom_registry=None, download_dir=None):
    """Initializes StackQL with the given options."""
    stackql_kwargs = {}
    if custom_registry:
        stackql_kwargs['custom_registry'] = custom_registry
    if download_dir:
        stackql_kwargs['download_dir'] = download_dir

    return StackQL(**stackql_kwargs)

def find_stackql_binary(stackql_bin_path, download_dir):
    """Find the stackql binary in the specified paths."""
    # First, try to use the binary path from StackQL instance
    if stackql_bin_path and os.path.isfile(stackql_bin_path):
        return stackql_bin_path

    # Next, try the download directory if provided
    if download_dir:
        binary_path = os.path.join(download_dir, 'stackql')
        return binary_path if os.path.isfile(binary_path) else None

    # If neither path works, return None
    return None

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
                raise click.BadParameter('environment variables must be formatted as KEY=VALUE')
    return env_vars

def setup_logger(command, args_dict):
    log_level = args_dict.get('log_level', 'INFO').upper()  # Normalize to uppercase
    valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}

    if log_level not in valid_levels:
        raise click.ClickException(
            f"Invalid log level: {log_level}. Valid levels are: {', '.join(valid_levels)}"
        )

    logger.setLevel(log_level)
    logger.debug(f"'{command}' command called with args: {str(args_dict)}")

def add_common_options(command):
    common_options = [
        click.option('--log-level', default='INFO', help='set the logging level.'),
        click.option('--env-file', default='.env', help='environment variables file.'),
        click.option(
            '-e',
            '--env',
            multiple=True,
            callback=parse_env_var,
            help='set additional environment variables.'
        ),
        click.option('--dry-run', is_flag=True, help='perform a dry run of the operation.'),
        click.option('--show-queries', is_flag=True, help='show queries run in the output logs.'),
        click.option(
            "--on-failure",
            type=click.Choice(["rollback", "ignore", "error"]),
            default="error",
            help="action on failure.",
        )
    ]
    for option in common_options:
        command = option(command)
    return command

def add_stackql_kwarg_options(command):
    """Add options that become kwargs for StackQL initialization."""
    stackql_options = [
        click.option('--custom-registry', default=None,
                    help='custom registry URL for StackQL.'),
        click.option('--download-dir', default=None,
                    help='download directory for StackQL.')
    ]
    for option in stackql_options:
        command = option(command)
    return command

#
# main entry point
#

@click.group()
@click.pass_context
def cli(ctx):
    """This is the main CLI entry point."""
    ctx.ensure_object(dict)

def setup_command_context(
    ctx,
    stack_dir,
    stack_env,
    log_level,
    env_file,
    env,
    dry_run,
    show_queries,
    on_failure,
    custom_registry,
    download_dir,
    command_name
):
    """Common initialization for commands."""
    # Initialize the logger
    setup_logger(command_name, locals())

    # Initialize the StackQL instance and environment variables
    stackql = get_stackql_instance(custom_registry, download_dir)

    # Load environment variables from the file and apply overrides
    env_vars = load_env_vars(env_file, env)
    return stackql, env_vars


#
# build command
#

@cli.command()
@click.argument('stack_dir')
@click.argument('stack_env')
@add_common_options
@add_stackql_kwarg_options
@click.pass_context
def build(ctx, stack_dir, stack_env, log_level, env_file,
          env, dry_run, show_queries, on_failure,
          custom_registry, download_dir ):
    """Create or update resources."""

    from .cmd.build import StackQLProvisioner

    stackql, env_vars = setup_command_context(
        ctx, stack_dir, stack_env, log_level, env_file,
        env, dry_run, show_queries, on_failure, custom_registry, download_dir, 'build'
    )
    provisioner = StackQLProvisioner(
        stackql, env_vars, logger, stack_dir, stack_env)
    stack_name_display = (
        provisioner.stack_name if provisioner.stack_name
        else stack_dir
    )
    message = (f"Deploying stack: [{stack_name_display}] "
               f"to environment: [{stack_env}]")
    print_unicode_box(message, BorderColor.YELLOW)

    provisioner.run(dry_run, show_queries, on_failure)
    click.echo("🎯 dry-run build complete" if dry_run
               else "🚀 build complete")

#
# teardown command
#

@cli.command()
@click.argument('stack_dir')
@click.argument('stack_env')
@add_common_options
@add_stackql_kwarg_options
@click.pass_context
def teardown(ctx, stack_dir, stack_env, log_level, env_file,
             env, dry_run, show_queries, on_failure,
             custom_registry, download_dir ):
    """Teardown a provisioned stack."""

    from .cmd.teardown import StackQLDeProvisioner

    stackql, env_vars = setup_command_context(
        ctx, stack_dir, stack_env, log_level, env_file,
        env, dry_run, show_queries, on_failure, custom_registry, download_dir, 'teardown'
    )
    deprovisioner = StackQLDeProvisioner(
        stackql, env_vars, logger, stack_dir, stack_env)
    stack_name_display = (
        deprovisioner.stack_name if deprovisioner.stack_name
        else stack_dir
    )
    message = (f"Tearing down stack: [{stack_name_display}] "
               f"in environment: [{stack_env}]")
    print_unicode_box(message, BorderColor.YELLOW)

    deprovisioner.run(dry_run, show_queries, on_failure)
    click.echo(f"🚧 teardown complete (dry run: {dry_run})")


#
# test command
#

@cli.command()
@click.argument('stack_dir')
@click.argument('stack_env')
@add_common_options
@add_stackql_kwarg_options
@click.pass_context
def test(ctx, stack_dir, stack_env, log_level, env_file,
         env, dry_run, show_queries, on_failure, custom_registry, download_dir):
    """Run test queries for the stack."""

    from .cmd.test import StackQLTestRunner

    stackql, env_vars = setup_command_context(
        ctx, stack_dir, stack_env, log_level, env_file,
        env, dry_run, show_queries, on_failure, custom_registry, download_dir, 'test'
    )
    test_runner = StackQLTestRunner(
        stackql, env_vars, logger, stack_dir, stack_env)
    stack_name_display = (
        test_runner.stack_name if test_runner.stack_name
        else stack_dir
    )
    message = (f"Testing stack: [{stack_name_display}] "
               f"in environment: [{stack_env}]")
    print_unicode_box(message, BorderColor.YELLOW)

    test_runner.run(dry_run, show_queries, on_failure)
    click.echo(f"🔍 tests complete (dry run: {dry_run})")

#
# info command
#

# stackql-deploy --custom-registry="https://registry-dev.stackql.app/providers" --download-dir . info
@cli.command()
@click.pass_context
def info(ctx):
    """Display version information for stackql-deploy and the stackql library."""
    stackql = get_stackql_instance(
        custom_registry=ctx.obj.get('custom_registry'),
        download_dir=ctx.obj.get('download_dir')
    )

    click.echo(click.style("stackql-deploy CLI", fg="green", bold=True))
    click.echo(f"  Version: {deploy_version}\n")

    click.echo(click.style("StackQL Library", fg="green", bold=True))
    click.echo(f"  Version: {stackql.version}")
    click.echo(f"  pystackql Version: {stackql.package_version}")
    click.echo(f"  Platform: {stackql.platform}")
    click.echo(f"  Binary Path: {stackql.bin_path}")
    if ctx.obj.get('custom_registry'):
        click.echo(f"  Custom Registry: {ctx.obj.get('custom_registry')}\n")
    else:
        click.echo("")

    click.echo(click.style("Installed Providers", fg="green", bold=True))
    providers = stackql.execute("SHOW PROVIDERS")
    for provider in providers:
        click.echo(f"  {provider['name']}: {provider['version']}")

    # Read and display contributors
    contributors = read_contributors(logger)
    if contributors:
        click.echo("\n" + click.style("✨ Special Thanks to our Contributors ✨", fg="green", bold=True))

        # Display 4 contributors per line
        for i in range(0, len(contributors), 4):
            # Get up to 4 contributors for this line
            line_contributors = contributors[i:i+4]
            # Join with commas
            line = ", ".join(line_contributors)
            # Display the line
            click.echo(f"  {line}")

def read_contributors(logger):
    """Read contributors from CSV file and return as list of dicts."""
    try:
        # Look for contributors.csv in package directory
        package_dir = os.path.dirname(os.path.abspath(__file__))
        contributors_path = os.path.join(package_dir, 'inc', 'contributors.csv')

        with open(contributors_path, 'r', encoding='utf-8') as f:
            contributors = [line.strip() for line in f if line.strip()]

        return contributors

    except Exception as e:
        logger.debug(f"Failed to read contributors: {str(e)}")
        return []

#
# shell command
#

@cli.command()
@click.pass_context
def shell(ctx):
    """Launch the stackql shell."""
    # Get an instance of StackQL with current context options
    stackql = get_stackql_instance(
        custom_registry=ctx.obj.get('custom_registry'),
        download_dir=ctx.obj.get('download_dir')
    )

    # Find the stackql binary path
    stackql_binary_path = find_stackql_binary(stackql.bin_path, ctx.obj.get('download_dir'))

    # If stackql binary is not found, fail with an error
    if not stackql_binary_path:
        click.echo("Error: StackQL binary not found in the specified paths.", err=True)
        sys.exit(1)

    click.echo(f"Launching stackql shell from: {stackql_binary_path}")

    # Launch the stackql shell as a subprocess
    try:
        subprocess.run([stackql_binary_path, "shell", "--colorscheme", "null"], check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error launching stackql shell: {e}", err=True)
        sys.exit(1)


#
# upgrade command
#

@cli.command()
@click.pass_context
def upgrade(ctx):
    """Upgrade the pystackql package and stackql binary to the latest version."""

    stackql = get_stackql_instance()
    orig_pkg_version = stackql.package_version
    orig_stackql_version = stackql.version
    stackql = None

    click.echo("upgrading pystackql package...")
    try:
        # Run the pip install command to upgrade pystackql
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "--quiet", "pystackql"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # click.echo(result.stdout.decode())
        click.echo("pystackql package upgraded successfully.")
    except subprocess.CalledProcessError as e:
        click.echo(f"Failed to upgrade pystackql: {e.stderr.decode()}", err=True)
    except Exception as e:
        click.echo(f"An error occurred: {str(e)}", err=True)

    stackql = get_stackql_instance()
    new_pkg_version = stackql.package_version
    if new_pkg_version == orig_pkg_version:
        click.echo(f"pystackql package version {orig_pkg_version} is already up-to-date.")
    else:
        click.echo(f"pystackql package upgraded from {orig_pkg_version} to {new_pkg_version}.")

    click.echo(f"upgrading stackql binary, current version {orig_stackql_version}...")
    stackql.upgrade()


#
# init command
#
SUPPORTED_PROVIDERS = {'aws', 'google', 'azure'}
DEFAULT_PROVIDER = 'azure'

def create_project_structure(stack_name, provider=None):
    stack_name = stack_name.replace('_', '-').lower()
    base_path = os.path.join(os.getcwd(), stack_name)
    if os.path.exists(base_path):
        raise click.ClickException(f"directory '{stack_name}' already exists.")

    directories = ['resources']
    for directory in directories:
        os.makedirs(os.path.join(base_path, directory), exist_ok=True)

    # Check if provider is supported
    if provider is None:
        logger.debug(f"provider not supplied, defaulting to `{DEFAULT_PROVIDER}`")
        provider = DEFAULT_PROVIDER
    elif provider not in SUPPORTED_PROVIDERS:
        provider = DEFAULT_PROVIDER
        message = (
            f"provider '{provider}' is not supported for `init`, "
            f"supported providers are: {', '.join(SUPPORTED_PROVIDERS)}, "
            f"defaulting to `{DEFAULT_PROVIDER}`"
        )
        click.secho(message, fg='yellow', err=False)

    # set template files
    if provider == 'google':
        sample_res_name = 'example_vpc'
    elif provider == 'azure':
        sample_res_name = 'example_res_grp'
    elif provider == 'aws':
        sample_res_name = 'example_vpc'

    template_base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', provider)
    env = Environment(loader=FileSystemLoader(template_base_path))

    logger.debug(f"template base path: {template_base_path}")

    template_files = {
        'stackql_manifest.yml.template': os.path.join(base_path, 'stackql_manifest.yml'),
        'README.md.template': os.path.join(base_path, 'README.md'),
        f'resources/{sample_res_name}.iql.template': os.path.join(base_path,'resources', f'{sample_res_name}.iql'),
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
@click.option(
    "--provider",
    default=None,
    help="[OPTIONAL] specify a provider to start your project, supported values: aws, azure, google",
)
def init(stack_name, provider):
    """Initialize a new stackql-deploy project structure."""
    setup_logger("init", locals())
    create_project_structure(stack_name, provider=provider)
    click.echo(f"project {stack_name} initialized successfully.")

#
# completion command
#

@cli.command("completion")
@click.argument(
    "shell",
    type=click.Choice(["bash", "zsh", "fish", "powershell"], case_sensitive=False),
    required=False,
)
@click.option("--install", is_flag=True, help="Install completion to shell profile")
def completion(shell, install):
    """
    Shell tab completion for stackql-deploy.
    Examples:
      eval "$(stackql-deploy completion bash)"     # activate now
      stackql-deploy completion bash --install     # install permanently
      stackql-deploy completion                    # auto-detect shell
    """

    # Auto-detect shell if not provided
    if not shell:
        shell = os.environ.get("SHELL", "").split("/")[-1] or "bash"
    shell = shell.lower()

    # Map shells to completion script files
    completion_scripts = {
        "bash": "stackql-deploy-completion.bash",
        "zsh": "stackql-deploy-completion.zsh",
        "fish": "stackql-deploy-completion.fish",
        "powershell": "stackql-deploy-completion.ps1"
    }

    script_name = completion_scripts.get(shell)
    if not script_name:
        click.echo(f"❌ Shell '{shell}' not supported. Supported: bash, zsh, fish, powershell", err=True)
        sys.exit(1)

    # Find the completion script
    script_path = _find_completion_script(script_name)
    if not script_path:
        click.echo(f"❌ Completion script not found: {script_name}", err=True)
        sys.exit(1)

    # Output script for eval/source (default behavior)
    if not install:
        with open(script_path, 'r') as f:
            click.echo(f.read())
        return

    # Install to shell profile
    _install_completion_for_shell(shell, script_path)

def _find_completion_script(script_name):
    """Find completion script in development or installed locations."""
    from pathlib import Path

    # Development mode: relative to project root
    cli_file = Path(__file__).resolve()
    project_root = cli_file.parent.parent
    dev_path = project_root / "shell_completions" / script_name

    if dev_path.exists():
        logger.debug(f"Found completion script: {dev_path}")
        return dev_path

    # Installed mode: check common install locations
    for prefix in [sys.prefix, sys.base_prefix, '/usr', '/usr/local']:
        installed_path = Path(prefix) / "share" / "stackql-deploy" / "completions" / script_name
        if installed_path.exists():
            logger.debug(f"Found completion script: {installed_path}")
            return installed_path

    logger.error(f"Completion script {script_name} not found")
    return None

def _install_completion_for_shell(shell, script_path):
    """Install completion to shell profile."""
    from pathlib import Path

    profiles = {
        "bash": Path.home() / ".bashrc",
        "zsh": Path.home() / ".zshrc",
        "fish": Path.home() / ".config/fish/config.fish",
        "powershell": Path.home() / "Documents/PowerShell/Microsoft.PowerShell_profile.ps1"
    }

    eval_commands = {
        "bash": 'eval "$(stackql-deploy completion bash)"',
        "zsh": 'eval "$(stackql-deploy completion zsh)"',
        "fish": 'stackql-deploy completion fish | source',
        "powershell": '. (stackql-deploy completion powershell)'
    }

    profile_path = profiles.get(shell)
    eval_cmd = eval_commands.get(shell)

    if not profile_path:
        click.echo(f"❌ Unknown profile for {shell}", err=True)
        return

    # Ensure profile directory and file exist
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    if not profile_path.exists():
        profile_path.touch()

    # Check if already installed
    try:
        content = profile_path.read_text()
        if "stackql-deploy completion" in content:
            click.echo(f"✅ Completion already installed in {profile_path}")
            _show_activation_instructions(shell)
            return
    except Exception as e:
        click.echo(f"❌ Error reading profile: {e}", err=True)
        return

    # Append completion line
    try:
        with open(profile_path, "a") as f:
            f.write(f"\n# stackql-deploy completion\n{eval_cmd}\n")
        click.echo(f"✅ Completion installed to {profile_path}")
        _show_activation_instructions(shell)
    except Exception as e:
        click.echo(f"❌ Error installing completion: {e}", err=True)

def _show_activation_instructions(shell):
    """Show shell-specific activation instructions."""
    instructions = {
        "bash": 'source ~/.bashrc',
        "zsh": 'source ~/.zshrc',
        "fish": 'source ~/.config/fish/config.fish',
        "powershell": '. $PROFILE'
    }

    click.echo(f"🚀 Activate now: {instructions.get(shell, 'restart your shell')}")
    click.echo("✨ Or restart your terminal")

cli.add_command(build)
cli.add_command(test)
cli.add_command(teardown)
cli.add_command(info)
cli.add_command(init)
cli.add_command(upgrade)
cli.add_command(shell)
cli.add_command(completion)

if __name__ == '__main__':
    cli()
