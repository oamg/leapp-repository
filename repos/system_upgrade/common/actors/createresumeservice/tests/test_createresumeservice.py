import os

import distro
import pytest


@pytest.mark.skipif(os.getuid() != 0, reason='User is not a root')
@pytest.mark.skipif(
    distro.linux_distribution()[0] == 'Fedora',
    reason='default.target.wants does not exists on Fedora distro',
)
def test_create_resume_service(current_actor_context):

    current_actor_context.run()

    service_name = 'leapp_resume.service'
    service_path = '/etc/systemd/system/{}'.format(service_name)
    symlink_path = '/etc/systemd/system/default.target.wants/{}'.format(service_name)

    try:
        assert os.path.isfile(service_path)
        assert os.path.isfile(symlink_path)
    finally:
        os.unlink(service_path)
        os.unlink(symlink_path)
