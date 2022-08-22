import os

from leapp import reporting
from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.models import Report, RootDirectory
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


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
        absolute_links_nonutf = [item for item in rootdir.invalid_items if item.target and os.path.isabs(item.target)]
        if not absolute_links and not absolute_links_nonutf:
            return

        report_fields = [
                reporting.Title('Upgrade requires links in root directory to be relative'),
                reporting.Summary(
                    'After rebooting, parts of the upgrade process can fail if symbolic links in / '
                    'point to absolute paths.\n'
                    'Please change these links to relative ones.'
                    ),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups([reporting.Groups.INHIBITOR])]

        # Generate reports about absolute links presence
        rem_commands = []
        if absolute_links:
            commands = []
            for item in absolute_links:
                command = ' '.join(['ln',
                                    '-snf',
                                    os.path.relpath(item.target, '/'),
                                    os.path.join('/', item.name)])
                commands.append(command)
            rem_commands = [['sh', '-c', ' && '.join(commands)]]
        # Generate reports about non-utf8 absolute links presence
        nonutf_count = len(absolute_links_nonutf)
        if nonutf_count > 0:
            # for non-utf encoded filenames can't provide a remediation command, so will mention this fact in a hint
            rem_hint = ("{} symbolic links point to absolute paths that have non-utf8 encoding and need to be"
                        " fixed additionally".format(nonutf_count))
            report_fields.append(reporting.Remediation(hint=rem_hint, commands=rem_commands))
        else:
            report_fields.append(reporting.Remediation(commands=rem_commands))

        reporting.create_report(report_fields)
