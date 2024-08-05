from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import PamUserDbLocation

FMT_LIST_SEPARATOR = "\n    - "


def process():
    msg = next(api.consume(PamUserDbLocation), None)
    if not msg:
        raise StopActorExecutionError('Expected PamUserDbLocation, but got None')

    if msg.locations:
        reporting.create_report([
            reporting.Title('pam_userdb databases will be converted to GDBM'),
            reporting.Summary(
                'On RHEL 10, GDMB is used by pam_userdb as it\'s backend database,'
                ' replacing BerkeleyDB. Existing pam_userdb databases will be'
                ' converted to GDBM. The following databases will be converted:'
                '{sep}{locations}'.format(sep=FMT_LIST_SEPARATOR, locations=FMT_LIST_SEPARATOR.join(msg.locations))),
            reporting.Severity(reporting.Severity.INFO),
            reporting.Groups([reporting.Groups.SECURITY, reporting.Groups.AUTHENTICATION])
        ])
    else:
        api.current_logger().debug(
            'No pam_userdb databases were located, thus nothing will be converted'
        )
