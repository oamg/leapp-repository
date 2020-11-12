from leapp import reporting
from leapp.libraries.common.config import architecture


def check_architecture():
    """Check if given architecture is supported by upgrade process"""
    if not architecture.matches_architecture(*architecture.ARCH_SUPPORTED):
        inhibit_upgrade()


def inhibit_upgrade():
    """Generate an upgrade inhibitor"""
    reporting.create_report(
        [
            reporting.Title('Unsupported architecture'),
            reporting.Summary(
                'Upgrade process is only supported on {} systems.'.format(
                    ', '.join(architecture.ARCH_SUPPORTED)
                )
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SANITY, reporting.Groups.INHIBITOR]),
        ]
    )
