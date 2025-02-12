from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import OutdatedKrb5conf

FMT_LIST_SEPARATOR = "\n    - "


def process():
    msg = next(api.consume(OutdatedKrb5conf), None)
    if not msg:
        raise StopActorExecutionError('Expected OutdatedKrb5conf, but got None')

    if msg.locations:
        reporting.create_report([
            reporting.Title('MIT krb5 configuration file(s) will be updated to point the new X.509 CA bundle file'),
            reporting.Summary(
                'On RHEL 10, the location of the reference X.509 CA bundle '
                'file was modified. The following MIT krb5 configuration files '
                'have to be updated to point to the new bundle file:'
                '{sep}{locations}'.format(sep=FMT_LIST_SEPARATOR, locations=FMT_LIST_SEPARATOR.join(msg.locations))),
            reporting.Severity(reporting.Severity.INFO),
            reporting.Groups([reporting.Groups.SECURITY, reporting.Groups.AUTHENTICATION])
        ])
    else:
        api.current_logger().debug(
            'No outdated X.509 CA bundle references were found in MIT krb5 '
            'configuration files, thus these files will remain unchanged.'
        )
