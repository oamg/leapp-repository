from leapp import reporting
from leapp.libraries.stdlib import api, run


related = [
    reporting.RelatedResource('package', 'ntpd'),
    reporting.RelatedResource('package', 'chrony'),
    reporting.RelatedResource('file', '/etc/chrony.conf'),
]


def is_config_default():
    """Check if the chrony config file was not modified since installation."""
    try:
        result = run(['rpm', '-V', '--nomtime', 'chrony'], checked=False)
        return '/etc/chrony.conf' not in result['stdout']
    except OSError as e:
        api.current_logger().warning("rpm verification failed: %s", str(e))
        return True


def check_chrony(chrony_installed):
    """Report potential issues in chrony configuration."""
    if not chrony_installed:
        api.current_logger().info('chrony package is not installed')
        return

    if is_config_default():
        reporting.create_report([
            reporting.Title('chrony using default configuration'),
            reporting.Summary(
                'default chrony configuration in RHEL8 uses leapsectz directive, which cannot be used with '
                'leap smearing NTP servers, and uses a single pool directive instead of four server directives'
            ),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups([
                    reporting.Groups.SERVICES,
                    reporting.Groups.TIME_MANAGEMENT
            ])
        ] + related)

    else:
        reporting.create_report([
            reporting.Title('chrony using non-default configuration'),
            reporting.Summary('chrony behavior will not change in RHEL8'),
            reporting.Severity(reporting.Severity.LOW),
            reporting.Groups([
                    reporting.Groups.SERVICES,
                    reporting.Groups.TIME_MANAGEMENT
            ])
        ] + related)
