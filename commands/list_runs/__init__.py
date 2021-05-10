from __future__ import print_function

import json
import sys

from leapp.cli.commands.upgrade.util import fetch_all_upgrade_contexts
from leapp.exceptions import CommandError
from leapp.utils.clicmd import command


@command('list-runs', help='List previous Leapp upgrade executions')
def list_runs(args):  # noqa; pylint: disable=unused-argument
    contexts = fetch_all_upgrade_contexts()
    if contexts:
        for context in contexts:
            print('Context ID: {} - time: {} - details: {}'.format(context[0], context[1], json.loads(context[2])),
                  file=sys.stdout)
    else:
        raise CommandError('No previous run found!')


def register(base_command):
    """
        Registers `leapp register`
    """
    base_command.add_sub(list_runs)
