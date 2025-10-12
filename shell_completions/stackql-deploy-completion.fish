# stackql-deploy completions for fish

# Remove any existing completions
complete -c stackql-deploy -e

# Main commands
complete -c stackql-deploy -n "__fish_use_subcommand" -a "build" -d "Create or update resources"
complete -c stackql-deploy -n "__fish_use_subcommand" -a "test" -d "Run test queries for the stack"
complete -c stackql-deploy -n "__fish_use_subcommand" -a "teardown" -d "Teardown a provisioned stack"
complete -c stackql-deploy -n "__fish_use_subcommand" -a "info" -d "Display version information"
complete -c stackql-deploy -n "__fish_use_subcommand" -a "init" -d "Initialize a new project structure"
complete -c stackql-deploy -n "__fish_use_subcommand" -a "upgrade" -d "Upgrade pystackql and stackql binary"
complete -c stackql-deploy -n "__fish_use_subcommand" -a "shell" -d "Launch the stackql shell"
complete -c stackql-deploy -n "__fish_use_subcommand" -a "completion" -d "Install tab completion"

# Common options for build/test/teardown
set -l common_cmds "build test teardown"

# --log-level
complete -c stackql-deploy -n "__fish_seen_subcommand_from $common_cmds" -l log-level -d "Set logging level" -a "DEBUG INFO WARNING ERROR CRITICAL"

# --env-file
complete -c stackql-deploy -n "__fish_seen_subcommand_from $common_cmds" -l env-file -d "Environment variables file" -r -F

# -e/--env
complete -c stackql-deploy -n "__fish_seen_subcommand_from $common_cmds" -s e -l env -d "Set additional environment variables"

# --dry-run
complete -c stackql-deploy -n "__fish_seen_subcommand_from $common_cmds" -l dry-run -d "Perform a dry run"

# --show-queries
complete -c stackql-deploy -n "__fish_seen_subcommand_from $common_cmds" -l show-queries -d "Show queries in output logs"

# --on-failure
complete -c stackql-deploy -n "__fish_seen_subcommand_from $common_cmds" -l on-failure -d "Action on failure" -a "rollback ignore error"

# --custom-registry
complete -c stackql-deploy -n "__fish_seen_subcommand_from $common_cmds" -l custom-registry -d "Custom registry URL"

# --download-dir
complete -c stackql-deploy -n "__fish_seen_subcommand_from $common_cmds" -l download-dir -d "Download directory" -r -a "(__fish_complete_directories)"

# --help
complete -c stackql-deploy -n "__fish_seen_subcommand_from $common_cmds" -l help -d "Show help message"

# build/test/teardown positional arguments
complete -c stackql-deploy -n "__fish_seen_subcommand_from $common_cmds; and not __fish_seen_argument -l log-level -l env-file -s e -l env -l dry-run -l show-queries -l on-failure -l custom-registry -l download-dir" -a "(__fish_complete_directories)" -d "Stack directory"

# Environment names (for second positional argument)
function __stackql_deploy_needs_env
    set -l cmd (commandline -opc)
    set -l cmd_count (count $cmd)
    # If we have: stackql-deploy build <dir> [<here>]
    if test $cmd_count -ge 3
        set -l has_opts 0
        for arg in $cmd[3..-1]
            if string match -q -- '-*' $arg
                set has_opts 1
                break
            end
        end
        if test $has_opts -eq 0
            return 0
        end
    end
    return 1
end

complete -c stackql-deploy -n "__fish_seen_subcommand_from $common_cmds; and __stackql_deploy_needs_env" -a "dev staging prod test prd sit uat" -d "Environment"

# init command
complete -c stackql-deploy -n "__fish_seen_subcommand_from init" -l provider -d "Specify provider" -a "aws google azure"
complete -c stackql-deploy -n "__fish_seen_subcommand_from init" -l help -d "Show help message"

# completion command
complete -c stackql-deploy -n "__fish_seen_subcommand_from completion" -a "bash zsh fish powershell" -d "Shell type"
complete -c stackql-deploy -n "__fish_seen_subcommand_from completion" -l install -d "Install completion"
complete -c stackql-deploy -n "__fish_seen_subcommand_from completion" -l help -d "Show help message"

# info/upgrade/shell commands
complete -c stackql-deploy -n "__fish_seen_subcommand_from info upgrade shell" -l help -d "Show help message"
complete -c stackql-deploy -n "__fish_seen_subcommand_from info upgrade shell" -l custom-registry -d "Custom registry URL"
complete -c stackql-deploy -n "__fish_seen_subcommand_from info upgrade shell" -l download-dir -d "Download directory" -r -a "(__fish_complete_directories)"
