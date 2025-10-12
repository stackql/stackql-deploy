# Shell Completions for stackql-deploy

This directory contains tab completion scripts for various shells.

## Automatic Installation

The easiest way to install completions:

```bash
stackql-deploy completion bash --install   # for bash
stackql-deploy completion zsh --install    # for zsh
stackql-deploy completion fish --install   # for fish
stackql-deploy completion powershell --install  # for PowerShell
```

### Activation

To activate immediately (`bash` example shown, similar logic for other shells):

```bash
eval "$(stackql-deploy completion bash)"
```

## Manual Installation

### Bash

```bash
# Add to ~/.bashrc
echo 'eval "$(stackql-deploy completion bash)"' >> ~/.bashrc
source ~/.bashrc
```

### Zsh

```bash
# Add to ~/.zshrc
echo 'eval "$(stackql-deploy completion zsh)"' >> ~/.zshrc
source ~/.zshrc
```

### Fish

```fish
# Add to ~/.config/fish/config.fish
echo 'stackql-deploy completion fish | source' >> ~/.config/fish/config.fish
source ~/.config/fish/config.fish
```

### PowerShell

```powershell
# Add to your PowerShell profile
Add-Content $PROFILE "`n# stackql-deploy completion`n. (stackql-deploy completion powershell)"
. $PROFILE
```

## Files

- `stackql-deploy-completion.bash` - Bash completion script
- `stackql-deploy-completion.zsh` - Zsh completion script
- `stackql-deploy-completion.fish` - Fish completion script
- `stackql-deploy-completion.ps1` - PowerShell completion script

All scripts are static (no Python subprocess calls) for instant performance.
