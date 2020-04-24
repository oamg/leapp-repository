import os

from leapp.libraries.stdlib import api, run
from leapp.models import SCTPConfig


def enable_sctp(_modprobe_d_path="/etc/modprobe.d"):
    """
    Enables the SCTP module by removing it from being black listed.
    :type _modprobe_d_path: str
    :param _modprobe_d_path: overwrite only in case of testing, by passing
        some tmp_dir instead
    """

    api.current_logger().info('Enabling SCTP.')
    run(['/usr/bin/sed', '-i', r's/^\s*blacklist.*sctp/#&/',
         os.path.join(_modprobe_d_path, 'sctp_diag-blacklist.conf'),
         os.path.join(_modprobe_d_path, 'sctp-blacklist.conf')])
    api.current_logger().info('Enabled SCTP.')


def perform_update():
    for sctpconfig in api.consume(SCTPConfig):
        api.current_logger().info('Consuming sctp={}'.format(sctpconfig.wanted))
        if sctpconfig.wanted:
            enable_sctp()
            break
