from leapp.libraries.common import reporting
from leapp.libraries.stdlib import api, run

import re

sysconfig_path = '/etc/sysconfig/memcached'

# Check if the memcached sysconfig file was not modified since installation
def is_sysconfig_default():
    try:
        result = run(['rpm', '-V', '--nomtime', 'memcached'], checked=False)
        return sysconfig_path not in result['stdout']
    except OSError as e:
        api.current_logger().warn("rpm verification failed: %s", str(e))
        return True

# Check if UDP port is disabled in the sysconfig file
def is_udp_disabled():
    with open(sysconfig_path) as f:
        for line in f:
            if re.match('^\\s*OPTIONS=.*-U\s*0[^0-9]', line):
                return True
    return False

# Report potential issues in memcached configuration
def check_memcached(memcached_installed):
    if not memcached_installed:
        api.current_logger().info('memcached package is not installed')
        return

    default_memcached_conf = is_sysconfig_default()
    disabled_udp_port = is_udp_disabled()

    if default_memcached_conf:
        reporting.report_generic(
                title='memcached service is using default configuration',
                summary='memcached in RHEL8 listens on loopback only and has UDP port disabled by default',
                severity='medium')
    elif not disabled_udp_port:
        reporting.report_generic(
                title='memcached has enabled UDP port',
                summary='memcached in RHEL7 has UDP port enabled by default, but it is disabled by default in RHEL8',
                severity='medium')
    else:
        reporting.report_generic(
                title='memcached has already disabled UDP port',
                summary='memcached in RHEL8 has UDP port disabled by default',
                severity='low')
