#compdef stackql-deploy

_stackql_deploy() {
    local -a commands
    commands=(
        'build:Create or update resources'
        'test:Run test queries for the stack'
        'teardown:Teardown a provisioned stack'
        'info:Display version information'
        'init:Initialize a new project structure'
        'upgrade:Upgrade pystackql and stackql binary'
        'shell:Launch the stackql shell'
        'completion:Install tab completion'
    )

    local -a common_opts
    common_opts=(
        '--log-level[Set logging level]:level:(DEBUG INFO WARNING ERROR CRITICAL)'
        '--env-file[Environment variables file]:file:_files -g "*.env"'
        '(-e --env)'{-e,--env}'[Set additional environment variables]:var:'
        '--dry-run[Perform a dry run]'
        '--show-queries[Show queries in output logs]'
        '--on-failure[Action on failure]:action:(rollback ignore error)'
        '--custom-registry[Custom registry URL]:url:'
        '--download-dir[Download directory]:dir:_directories'
        '--help[Show help message]'
    )

    _arguments -C \
        '1: :->command' \
        '*::arg:->args'

    case $state in
        command)
            _describe -t commands 'stackql-deploy commands' commands
            ;;
        args)
            case $words[1] in
                build|test|teardown)
                    if (( CURRENT == 2 )); then
                        _arguments '2:stack directory:_directories'
                    elif (( CURRENT == 3 )); then
                        _arguments '3:environment:(dev staging prod test prd sit uat)'
                    else
                        _arguments $common_opts
                    fi
                    ;;
                init)
                    _arguments \
                        '2:stack name:' \
                        '--provider[Specify provider]:provider:(aws google azure)' \
                        '--help[Show help message]'
                    ;;
                completion)
                    _arguments \
                        '2:shell:(bash zsh fish powershell)' \
                        '--install[Install completion]' \
                        '--help[Show help message]'
                    ;;
                info|upgrade|shell)
                    _arguments \
                        '--help[Show help message]' \
                        '--custom-registry[Custom registry URL]:url:' \
                        '--download-dir[Download directory]:dir:_directories'
                    ;;
            esac
            ;;
    esac
}

_stackql_deploy "$@"
