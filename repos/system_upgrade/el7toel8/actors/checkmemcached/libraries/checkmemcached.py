import re

from leapp import reporting
from leapp.libraries.stdlib import api, run


COMMON_REPORT_GROUPS = [reporting.Groups.SERVICES]


sysconfig_path = '/etc/sysconfig/memcached'

related = [
    reporting.RelatedResource('package', 'memcached'),
    reporting.RelatedResource('file', sysconfig_path)
]


def is_sysconfig_default():
    """Check if the memcached sysconfig file was not modified since installation."""
    try:
        result = run(['rpm', '-V', '--nomtime', 'memcached'], checked=False)
        return sysconfig_path not in result['stdout']
    except OSError as e:
        api.current_logger().warning("rpm verification failed: %s", str(e))
        return True


def is_udp_disabled():
    """Check if UDP port is disabled in the sysconfig file."""
    with open(sysconfig_path) as f:
        for line in f:
            if re.match(r'^\s*OPTIONS=.*-U\s*0[^0-9]', line):
                return True
    return False


def check_memcached(memcached_installed):
    """Report potential issues in memcached configuration."""
    if not memcached_installed:
        api.current_logger().info('memcached package is not installed')
        return

    default_memcached_conf = is_sysconfig_default()
    disabled_udp_port = is_udp_disabled()

    if default_memcached_conf:
        reporting.create_report([
            reporting.Title('memcached service is using default configuration'),
            reporting.Summary('memcached in RHEL8 listens on loopback only and has UDP port disabled by default'),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups(COMMON_REPORT_GROUPS),
        ] + related)

    elif not disabled_udp_port:
        reporting.create_report([
            reporting.Title('memcached has enabled UDP port'),
            reporting.Summary(
                'memcached in RHEL7 has UDP port enabled by default, but it is disabled by default in RHEL8'
            ),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups(COMMON_REPORT_GROUPS),
        ] + related)

    else:
        reporting.create_report([
            reporting.Title('memcached has already disabled UDP port'),
            reporting.Summary('memcached in RHEL8 has UDP port disabled by default'),
            reporting.Severity(reporting.Severity.LOW),
            reporting.Groups(COMMON_REPORT_GROUPS),
        ] + related)
