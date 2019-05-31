import os
import errno

from leapp.snactor.fixture import current_actor_context


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
