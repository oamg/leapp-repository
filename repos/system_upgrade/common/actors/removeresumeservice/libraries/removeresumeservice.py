import errno
import os

from leapp import reporting
from leapp.libraries.stdlib import api, run
from leapp.reporting import create_report

SYSTEMD_DIR = '/etc/systemd/system'
SERVICE_NAME = 'leapp_resume.service'
WANTS_TARGETS = ('multi-user.target', 'default.target')


def _unlink_if_exists(path):
    """Unlink path; ignore if it is already gone (e.g. after systemctl disable)."""
    try:
        os.unlink(path)
    except OSError as err:
        if err.errno == errno.ENOENT:
            return
        api.current_logger().debug('Failed removing {}: {}'.format(path, err))
        raise


def process():
    service_path = os.path.join(SYSTEMD_DIR, SERVICE_NAME)
    if os.path.isfile(service_path):
        run(['systemctl', 'disable', SERVICE_NAME])
        _unlink_if_exists(service_path)
        for target in WANTS_TARGETS:
            wants_path = os.path.join(
                SYSTEMD_DIR, '{}.wants'.format(target), SERVICE_NAME
            )
            _unlink_if_exists(wants_path)

    create_report([
        reporting.Title('"{}" service deleted'.format(SERVICE_NAME)),
        reporting.Summary(
            '"{}" was taking care of resuming upgrade process '
            'after the first reboot.'.format(SERVICE_NAME)),
        reporting.Groups([reporting.Groups.UPGRADE_PROCESS]),
    ])
