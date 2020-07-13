import errno
import os

import pytest


@pytest.mark.skipif(
    not os.path.isdir('/etc/systemd/system/default.target.wants')
    or not os.getuid() == 0,
    reason='default.target.wants dir should exists and test should be run '
           'under the root user.',
)
# TODO make the test not destructive
@pytest.mark.skipif(os.getenv("DESTRUCTIVE_TESTING", False) in [False, "0"],
                    reason='Test disabled by default because it would modify the system')
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
