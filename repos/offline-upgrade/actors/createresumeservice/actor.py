import shutil
import os

from leapp.actors import Actor
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag
from leapp.models import FinalReport


class CreateSystemdResumeService(Actor):
    name = 'create_systemd_service'
    description = ('Create a systemd service which will resume leapp '
                  'upgrade after the first reboot')
    consumes = ()
    produces = (FinalReport,)
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

        self.produce(FinalReport(
            severity='Info',
            result='Pass',
            summary='Leapp resume systemd service enabled',
            details='{} enabled as oneshot systemd service to resume Leapp execution '
                    'after reboot'.format(service_name)))
