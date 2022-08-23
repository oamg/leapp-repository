import os

from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import TransactionCompleted
from leapp.tags import IPUWorkflowTag, RPMUpgradePhaseTag


class PythonThreeTmpWorkaround(Actor):
    """
    Create the /usr/bin/python3 alternative if not exists.

    During the RPM upgrade the /usr/bin/python3 is removed because of problem
    in alternatives. The fix requires new builds of python36 on RHEL8, python3
    on RHEL 9 and alternatives on both systems. Once the internal repositories
    are updated, we can drop this. If the /usr/bin/python3 file exists,
    do nothing.
    """

    name = 'pythonthreetmpworkaround'
    consumes = (TransactionCompleted,)
    produces = ()
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        if os.path.isfile('/usr/bin/python3'):
            api.current_logger().info('The python3 file exists. the actor can be removed probably.')
            return

        cmd = [
            'alternatives', '--install', '/usr/bin/python3', 'python3', '/usr/bin/python3.9', '1000000',
        ]

        sub_cmds = [
            ['--slave', '/usr/share/man/man1/python3.1.gz', 'python3-man', '/usr/share/man/man1/python3.9.1.gz'],
            ['--slave', '/usr/bin/pip3', 'pip3', '/usr/bin/pip3.9'],
            ['--slave', '/usr/bin/pip-3', 'pip-3', '/usr/bin/pip-3.9'],
            ['--slave', '/usr/bin/easy_install-3', 'easy_install-3', '/usr/bin/easy_install-3.9'],
            ['--slave', '/usr/bin/pydoc3', 'pydoc3', '/usr/bin/pydoc3.9'],
            ['--slave', '/usr/bin/pydoc-3', 'pydoc-3', '/usr/bin/pydoc3.9'],
            ['--slave', '/usr/bin/pyvenv-3', 'pyvenv-3', '/usr/bin/pyvenv-3.9'],
        ]

        for sub_cmd in sub_cmds:
            if os.path.exists(sub_cmd[1]):
                # some rhel 9 packages are already updated and handle
                # alternatives correctly using the --keep-foreign option
                continue
            cmd += sub_cmd

        try:
            run(cmd)
        except CalledProcessError as exc:
            raise StopActorExecutionError(
                message='Cannot create python3 alternatives; upgrade cannot be finished',
                details={'details': str(exc), 'stderr': exc.stderr},
            )
