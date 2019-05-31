from leapp.libraries.common import reporting
from leapp.libraries.stdlib import api, run


def is_config_default():
    """Check if the chrony config file was not modified since installation."""
    try:
        result = run(['rpm', '-V', '--nomtime', 'chrony'], checked=False)
        return '/etc/chrony.conf' not in result['stdout']
    except OSError as e:
        api.current_logger().warn("rpm verification failed: %s", str(e))
        return True


def check_chrony(chrony_installed):
    """Report potential issues in chrony configuration."""
    if not chrony_installed:
        api.current_logger().info('chrony package is not installed')
        return

    if is_config_default():
        reporting.report_generic(
            title='chrony using default configuration',
            summary='default chrony configuration in RHEL8 uses leapsectz directive, which cannot be used with '
            'leap smearing NTP servers, and uses a single pool directive instead of four server directives',
            severity='medium')
    else:
        reporting.report_generic(
            title='chrony using non-default configuration',
            summary='chrony behavior will not change in RHEL8',
            severity='low')
