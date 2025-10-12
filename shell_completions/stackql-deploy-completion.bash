_stackql_deploy_completion() {
    local cur prev opts base
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    # Main commands
    local commands="build test teardown info init upgrade shell completion"
    
    # Common options for build/test/teardown
    local common_opts="--log-level --env-file -e --env --dry-run --show-queries --on-failure --custom-registry --download-dir --help"
    
    # Get the command (first non-option argument)
    local cmd=""
    for ((i=1; i<${#COMP_WORDS[@]}-1; i++)); do
        if [[ ${COMP_WORDS[i]} != -* ]]; then
            cmd=${COMP_WORDS[i]}
            break
        fi
    done
    
    # Completion logic
    case "${cmd}" in
        build|test|teardown)
            # After command, need stack_dir then stack_env
            local args=()
            for ((i=2; i<${#COMP_WORDS[@]}-1; i++)); do
                if [[ ${COMP_WORDS[i]} != -* ]]; then
                    args+=("${COMP_WORDS[i]}")
                fi
            done
            
            if [ ${#args[@]} -eq 0 ]; then
                # Complete directory names for stack_dir
                compopt -o dirnames
                COMPREPLY=( $(compgen -d -- "${cur}") )
            elif [ ${#args[@]} -eq 1 ]; then
                # Complete common environment names
                COMPREPLY=( $(compgen -W "dev staging prod test prd sit uat" -- "${cur}") )
            else
                # Complete options
                COMPREPLY=( $(compgen -W "${common_opts}" -- "${cur}") )
            fi
            ;;
        
        init)
            # init <stack_name> [--provider]
            case "${prev}" in
                --provider)
                    COMPREPLY=( $(compgen -W "aws google azure" -- "${cur}") )
                    ;;
                init)
                    # Just type the stack name, no completion
                    ;;
                *)
                    COMPREPLY=( $(compgen -W "--provider --help" -- "${cur}") )
                    ;;
            esac
            ;;
        
        completion)
            COMPREPLY=( $(compgen -W "bash zsh fish powershell" -- "${cur}") )
            ;;
        
        info|upgrade|shell)
            COMPREPLY=( $(compgen -W "--help --custom-registry --download-dir" -- "${cur}") )
            ;;
        
        *)
            # No command yet, show main commands and global options
            if [[ ${cur} == -* ]]; then
                COMPREPLY=( $(compgen -W "--help --version" -- "${cur}") )
            else
                COMPREPLY=( $(compgen -W "${commands}" -- "${cur}") )
            fi
            ;;
    esac
    
    # Handle option arguments
    case "${prev}" in
        --log-level)
            COMPREPLY=( $(compgen -W "DEBUG INFO WARNING ERROR CRITICAL" -- "${cur}") )
            return 0
            ;;
        --env-file)
            compopt -o default
            COMPREPLY=( $(compgen -f -X '!*.env' -- "${cur}") $(compgen -d -- "${cur}") )
            return 0
            ;;
        --on-failure)
            COMPREPLY=( $(compgen -W "rollback ignore error" -- "${cur}") )
            return 0
            ;;
        --custom-registry)
            # URL completion - just let user type
            return 0
            ;;
        --download-dir)
            compopt -o dirnames
            COMPREPLY=( $(compgen -d -- "${cur}") )
            return 0
            ;;
    esac
    
    return 0
}

complete -F _stackql_deploy_completion stackql-deploy
