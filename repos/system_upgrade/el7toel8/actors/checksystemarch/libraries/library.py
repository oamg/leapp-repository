from leapp import reporting
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api


def check_architecture():
    """Check if given architecture is supported by upgrade process"""
    if not architecture.matches_architecture(*architecture.ARCH_ACCEPTED):
        inhibit_upgrade()


def inhibit_upgrade():
    """Generate an upgrade inhibitor"""
    reporting.create_report(
        [
            reporting.Title(
                'Unsupported architecture [{}]'.format(
                    api.current_actor().configuration.architecture
                )
            ),
            reporting.Summary(
                'Upgrade process is only supported on {} systems.'.format(
                    ', '.join(architecture.ARCH_ACCEPTED)
                )
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags([reporting.Tags.SANITY]),
            reporting.Flags([reporting.Flags.INHIBITOR]),
        ]
    )
