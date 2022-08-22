import errno
import os

from leapp import reporting
from leapp.actors import Actor
from leapp.libraries.stdlib import api, run
from leapp.reporting import create_report, Report
from leapp.tags import FirstBootPhaseTag, IPUWorkflowTag


class RemoveSystemdResumeService(Actor):
    """
    Remove systemd service to launch Leapp.

    After system was rebooted and process resumed, this service is not necessary anymore.
    """

    name = 'remove_systemd_resume_service'
    consumes = ()
    produces = (Report,)
    tags = (FirstBootPhaseTag.After, IPUWorkflowTag)

    def process(self):
        service_name = 'leapp_resume.service'
        if os.path.isfile('/etc/systemd/system/{}'.format(service_name)):
            run(['systemctl', 'disable', service_name])
            paths_to_unlink = [
                '/etc/systemd/system/{}'.format(service_name),
                '/etc/systemd/system/default.target.wants/{}'.format(service_name),
            ]
            for path in paths_to_unlink:
                try:
                    os.unlink(path)
                except OSError as e:
                    api.current_logger().debug('Failed removing {}: {}'.format(path, str(e)))
                    if e.errno != errno.ENOENT:
                        raise

        create_report([
            reporting.Title('"{}" service deleted'.format(service_name)),
            reporting.Summary(
                '"{}" was taking care of resuming upgrade process '
                'after the first reboot.'.format(service_name)),
            reporting.Groups([reporting.Groups.UPGRADE_PROCESS]),
        ])
