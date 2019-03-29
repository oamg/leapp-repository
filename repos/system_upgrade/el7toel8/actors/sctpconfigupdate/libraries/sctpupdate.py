from leapp.libraries.stdlib import api, run
from leapp.models import SCTPConfig


def enable_sctp():
    """
    Enables the SCTP module by removing it from being black listed.
    """

    api.current_logger().info('Enabling SCTP.')
    run(['/usr/bin/sed', '-i', 's/^\s*blacklist.*sctp/#&/',
         '/etc/modprobe.d/sctp_diag-blacklist.conf',
         '/etc/modprobe.d/sctp-blacklist.conf'])
    api.current_logger().info('Enabled SCTP.')


def perform_update():
    for sctpconfig in api.consume(SCTPConfig):
        api.current_logger().info('Consuming sctp={}'.format(sctpconfig.wanted))
        if sctpconfig.wanted:
            enable_sctp()
            break
