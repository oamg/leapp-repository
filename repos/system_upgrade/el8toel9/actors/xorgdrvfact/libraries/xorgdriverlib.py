#
# Helper functions
#

import re

from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import XorgDrv


def check_drv_and_options(driver, logs):
    regex_driver = re.compile(''.join([driver, '.*DPI set to']))
    regex_options = re.compile(''.join([r'\(\*\*\)', '.*', driver]))
    has_driver = False
    has_options = False

    for line in logs:
        if re.search(regex_driver, line):
            has_driver = True
        if re.search(regex_options, line):
            has_options = True

    if not has_driver:
        return None

    return XorgDrv(driver=driver, has_options=has_options)


def get_xorg_logs_from_journal():
    try:
        output = run(['/usr/bin/journalctl', '/usr/libexec/Xorg', '-o', 'cat', '-b', '0'], split=True)
    except CalledProcessError:
        api.current_logger().debug('No Xorg logs found in journal.')
        return []

    return output['stdout']
