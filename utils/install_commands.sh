#!/bin/bash

LEAPP_CLI_COMMANDS_PATH=$($1 -c "import leapp.cli.commands; print(leapp.cli.commands.__path__[0])")
echo "Installing commands to \"$LEAPP_CLI_COMMANDS_PATH\""
for folder in `ls -1 commands/`; do
    if [[ $folder != "tests" ]]; then
        cp -a commands/$folder $LEAPP_CLI_COMMANDS_PATH;
    fi
done
