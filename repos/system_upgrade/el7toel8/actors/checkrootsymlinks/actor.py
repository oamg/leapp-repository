import os

from leapp import reporting
from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.models import Report, RootDirectory
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag


class CheckRootSymlinks(Actor):
    """
    Check if the symlinks /bin and /lib are relative, not absolute.

    After reboot, dracut fails if the links are absolute.
    """

    name = 'check_root_symlinks'
    consumes = (RootDirectory,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        rootdir = next(self.consume(RootDirectory), None)
        if not rootdir:
            raise StopActorExecutionError('Cannot check root symlinks',
                                          details={'Problem': 'Did not receive a message with '
                                                              'root subdirectories'})
        absolute_links = [item for item in rootdir.items if item.target and os.path.isabs(item.target)]

        if absolute_links:
            commands = [' '.join(['ln', '-snf',
                                  os.path.relpath(item.target, '/'),
                                  os.path.join('/', item.name)]) for item in absolute_links]
            remediation = [['sh', '-c', ' && '.join(commands)]]
            reporting.create_report([
                reporting.Title('Upgrade requires links in root directory to be relative'),
                reporting.Summary(
                    'After rebooting, parts of the upgrade process can fail if symbolic links in / '
                    'point to absolute paths.\n'
                    'Please change these links to relative ones.'
                ),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups([reporting.Groups.INHIBITOR]),
                reporting.Remediation(commands=remediation)
            ])
