from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.distro import DISTRO_REPORT_NAMES
from leapp.libraries.stdlib import api, format_list
from leapp.models import PamUserDbLocation


def process():
    msg = next(api.consume(PamUserDbLocation), None)
    if not msg:
        raise StopActorExecutionError('Expected PamUserDbLocation, but got None')

    if msg.locations:
        reporting.create_report([
            reporting.Title('pam_userdb databases will be converted to GDBM'),
            reporting.Summary(
                'On {target_distro} 10, GDMB is used by pam_userdb as it\'s backend database,'
                ' replacing BerkeleyDB. Existing pam_userdb databases will be'
                ' converted to GDBM. The following databases will be converted:'
                '{locations}'.format(
                    locations=format_list(msg.locations),
                    target_distro=DISTRO_REPORT_NAMES.target,
                )
            ),
            reporting.Severity(reporting.Severity.INFO),
            reporting.Groups([reporting.Groups.SECURITY, reporting.Groups.AUTHENTICATION])
        ])
    else:
        api.current_logger().debug(
            'No pam_userdb databases were located, thus nothing will be converted'
        )
