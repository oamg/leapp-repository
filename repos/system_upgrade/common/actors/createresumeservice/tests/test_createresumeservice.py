import os

import pytest


@pytest.mark.skipif(os.getuid() != 0, reason='User is not a root')
def test_create_resume_service(current_actor_context):
    current_actor_context.run()

    systemd_dir = '/etc/systemd/system'
    service_name = 'leapp_resume.service'
    target_name = 'multi-user.target'

    service_path = os.path.join(systemd_dir, service_name)
    symlink_path = os.path.join(systemd_dir, '{}.wants'.format(target_name), service_name)

    try:
        assert os.path.isfile(service_path)
        assert os.path.isfile(symlink_path)
    finally:
        os.unlink(service_path)
        os.unlink(symlink_path)
