import shutil
import os

from leapp.exceptions import StopActorExecutionError
from leapp.actors import Actor
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag
from leapp.reporting import Report, create_report
from leapp import reporting


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
