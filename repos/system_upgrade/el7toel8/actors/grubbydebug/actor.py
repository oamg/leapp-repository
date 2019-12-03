import os

from leapp.actors import Actor
from leapp.models import TransactionCompleted
from leapp.tags import RPMUpgradePhaseTag, IPUWorkflowTag, ExperimentalTag
from leapp.libraries.stdlib import api, run, CalledProcessError


GRUBBY_FILES = ['/usr/libexec/grubby/grubby-bls', '/usr/libexec/grubby/grubby']
DEBUG_FLAG = 'set -x\n'


class GrubbyDebug(Actor):
    """
    Temporary experimental debug actor to add "set -x" option in grubby scripts
    """

    name = 'grubby_debug'
    consumes = (TransactionCompleted,)
    produces = ()
    tags = (ExperimentalTag, RPMUpgradePhaseTag, IPUWorkflowTag, )

    def process(self):

        def enable_debug(filename):
            with open(filename, 'r') as fo_read:
                content = fo_read.readlines()
                if DEBUG_FLAG in content:
                    return
                shebang_line = 0
                for i, line in enumerate(content):
                    if line.startswith('#!/bin/bash'):
                        shebang_line = i
                        break
                content.insert(shebang_line+1, DEBUG_FLAG)

            with open(filename, 'w') as fo_write:
                content = ''.join(content)
                fo_write.write(content)

        for file_ in GRUBBY_FILES:
            if os.path.exists(file_):
                try:
                    enable_debug(file_)
                except (IOError, OSError):
                    api.current_logger().warning(
                        'Failed to activate debug mode in {}'.format(file_), exc_info=True)

        try:
            run(['ls', '-la', '/boot'])
        except CalledProcessError:
            api.current_logger().warning(
                'Could not list /boot dir', exc_info=True)
        try:
            run(['sh', '-c', 'cat /boot/loader/entries/*.conf'])
        except CalledProcessError:
            api.current_logger().warning(
                'Could not show all BLS entries', exc_info=True)
