#!/bin/sh
# script read at startup by login shells
# in the initramfs this is read for example by the emergency shell

# set the environment file, containing shell commands to execute at startup of
# interactive shells
if [ -f "$HOME/.shrc" ]; then
    ENV="$HOME/.shrc"; export ENV
fi
