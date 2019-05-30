import shutil
import os

from leapp.actors import Actor
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag
from leapp.reporting import Report
from leapp.libraries.common.reporting import report_generic


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
        service_templ_fpath = self.get_file_path(service_name)
        shutil.copyfile(service_templ_fpath, os.path.join(
            '/etc/systemd/system/', service_name))

        service_path = '/etc/systemd/system/{}'.format(service_name)
        symlink_path = '/etc/systemd/system/default.target.wants/{}'.format(service_name)

        try:
            os.symlink(service_path, symlink_path)
        except OSError as e:
            self.report_error('Could not create a symlink to enable {}'.format(service_name),
                              details=str(e))
            return

        report_generic(
            title='Leapp resume systemd service enabled',
            summary='{} enabled as oneshot systemd service to resume Leapp execution '
                    'after reboot.'.format(service_name),
            severity='low')
