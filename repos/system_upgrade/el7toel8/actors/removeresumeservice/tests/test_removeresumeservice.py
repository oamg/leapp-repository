import os
import errno

import distro
import pytest

from leapp.snactor.fixture import current_actor_context


@pytest.mark.skipif(
    distro.linux_distribution()[0] == 'Fedora',
    reason='default.target.wants does not exists on Fedora distro',
    )
def test_remove_resume_service(current_actor_context):
    service_name = 'leapp_resume.service'
    service_path = os.path.join('/etc/systemd/system/', service_name)
    symlink_path = os.path.join('/etc/systemd/system/default.target.wants/', service_name)

    # lets make sure there are not leftovers from previous tests
    try:
        os.unlink(service_path)
        os.unlink(symlink_path)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

    with open(service_path, 'w'):
        pass

    os.symlink(service_path, symlink_path)

    current_actor_context.run()

    assert not os.path.isfile(service_path)
    assert not os.path.isfile(symlink_path)
