import os
import shutil

from leapp import reporting
from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.reporting import create_report, Report
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag


class CreateSystemdResumeService(Actor):
    """
    Add a systemd service to launch Leapp.

    Create a systemd service which will resume Leapp upgrade after the first reboot.
    """

    name = 'create_systemd_service'
    consumes = ()
    produces = (Report,)
    tags = (FinalizationPhaseTag, IPUWorkflowTag)

    def process(self):
        service_name = 'leapp_resume.service'
        systemd_dir = '/etc/systemd/system'

        service_templ_fpath = self.get_file_path(service_name)
        shutil.copyfile(service_templ_fpath, os.path.join(systemd_dir, service_name))

        service_path = '/etc/systemd/system/{}'.format(service_name)
        symlink_path = '/etc/systemd/system/default.target.wants/{}'.format(service_name)

        # in case nothing is enabled in the default target, the directory does not exist
        try:
            os.mkdir(os.path.join(systemd_dir, 'default.target.wants'))
        except OSError:
            pass

        if os.path.exists(symlink_path):
            api.current_logger().debug(
                'Symlink {} already exists (from previous upgrade?). Removing... '.format(symlink_path)
            )
            os.unlink(symlink_path)

        try:
            os.symlink(service_path, symlink_path)
        except OSError as e:
            raise StopActorExecutionError(
                    'Could not create a symlink to enable {}'.format(service_name),
                    details={"details": str(e)})

        create_report([
            reporting.Title('Leapp resume systemd service enabled'),
            reporting.Summary(
                '{} enabled as oneshot systemd service to resume Leapp execution '
                'after reboot.'.format(service_name)
            ),
            reporting.Severity(reporting.Severity.INFO),
            reporting.Groups([reporting.Groups.UPGRADE_PROCESS]),
            reporting.RelatedResource('file', service_path),
            reporting.RelatedResource('file', symlink_path),
            reporting.RelatedResource('service', service_name)
        ])
