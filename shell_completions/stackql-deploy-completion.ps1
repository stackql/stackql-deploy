# stackql-deploy PowerShell completion

using namespace System.Management.Automation
using namespace System.Management.Automation.Language

Register-ArgumentCompleter -Native -CommandName stackql-deploy -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $commands = @{
        'build' = 'Create or update resources'
        'test' = 'Run test queries for the stack'
        'teardown' = 'Teardown a provisioned stack'
        'info' = 'Display version information'
        'init' = 'Initialize a new project structure'
        'upgrade' = 'Upgrade pystackql and stackql binary'
        'shell' = 'Launch the stackql shell'
        'completion' = 'Install tab completion'
    }

    $commonOptions = @{
        '--log-level' = @('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        '--env-file' = @()  # File completion
        '-e' = @()
        '--env' = @()
        '--dry-run' = @()
        '--show-queries' = @()
        '--on-failure' = @('rollback', 'ignore', 'error')
        '--custom-registry' = @()
        '--download-dir' = @()  # Directory completion
        '--help' = @()
    }

    $environments = @('dev', 'staging', 'prod', 'test', 'prd', 'sit', 'uat')
    $providers = @('aws', 'google', 'azure')
    $shells = @('bash', 'zsh', 'fish', 'powershell')

    # Parse command line
    $tokens = $commandAst.ToString().Split(' ', [StringSplitOptions]::RemoveEmptyEntries)
    $command = $null
    $argCount = 0

    for ($i = 1; $i -lt $tokens.Count; $i++) {
        if ($tokens[$i] -notmatch '^-') {
            if ($null -eq $command) {
                $command = $tokens[$i]
            } else {
                $argCount++
            }
        }
    }

    # Complete based on position
    if ($null -eq $command) {
        # Complete main commands
        $commands.GetEnumerator() | Where-Object { $_.Key -like "$wordToComplete*" } | ForEach-Object {
            [CompletionResult]::new($_.Key, $_.Key, 'ParameterValue', $_.Value)
        }
        return
    }

    # Command-specific completion
    switch ($command) {
        { $_ -in 'build', 'test', 'teardown' } {
            if ($argCount -eq 0) {
                # Complete directories for stack_dir
                Get-ChildItem -Directory -Path . -Filter "$wordToComplete*" | ForEach-Object {
                    [CompletionResult]::new($_.Name, $_.Name, 'ParameterValue', 'Stack directory')
                }
            }
            elseif ($argCount -eq 1) {
                # Complete environment names
                $environments | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [CompletionResult]::new($_, $_, 'ParameterValue', 'Environment')
                }
            }
            else {
                # Complete options
                $commonOptions.GetEnumerator() | Where-Object { $_.Key -like "$wordToComplete*" } | ForEach-Object {
                    [CompletionResult]::new($_.Key, $_.Key, 'ParameterName', $_.Key)
                }
            }
        }

        'init' {
            if ($wordToComplete -like '--*') {
                '--provider', '--help' | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }
            elseif ($tokens[-2] -eq '--provider') {
                $providers | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [CompletionResult]::new($_, $_, 'ParameterValue', 'Provider')
                }
            }
        }

        'completion' {
            if ($argCount -eq 0) {
                $shells | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [CompletionResult]::new($_, $_, 'ParameterValue', 'Shell type')
                }
            }
            '--install', '--help' | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                [CompletionResult]::new($_, $_, 'ParameterName', $_)
            }
        }

        { $_ -in 'info', 'upgrade', 'shell' } {
            if ($wordToComplete -like '--*') {
                '--help', '--custom-registry', '--download-dir' | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                    [CompletionResult]::new($_, $_, 'ParameterName', $_)
                }
            }
        }
    }

    # Handle option values
    $lastToken = $tokens[-2]
    switch ($lastToken) {
        '--log-level' {
            $commonOptions['--log-level'] | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                [CompletionResult]::new($_, $_, 'ParameterValue', 'Log level')
            }
        }
        '--on-failure' {
            $commonOptions['--on-failure'] | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                [CompletionResult]::new($_, $_, 'ParameterValue', 'Failure action')
            }
        }
        '--env-file' {
            Get-ChildItem -File -Path . -Filter "*$wordToComplete*.env" | ForEach-Object {
                [CompletionResult]::new($_.Name, $_.Name, 'ParameterValue', 'Environment file')
            }
        }
        '--download-dir' {
            Get-ChildItem -Directory -Path . -Filter "$wordToComplete*" | ForEach-Object {
                [CompletionResult]::new($_.Name, $_.Name, 'ParameterValue', 'Download directory')
            }
        }
        '--provider' {
            $providers | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                [CompletionResult]::new($_, $_, 'ParameterValue', 'Provider')
            }
        }
    }
}
