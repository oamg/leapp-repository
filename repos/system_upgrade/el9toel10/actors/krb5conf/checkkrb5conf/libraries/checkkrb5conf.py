from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import OutdatedKrb5conf

FMT_LIST_SEPARATOR = "\n    - "


def __human_readable_list(unmanaged_files):
    if unmanaged_files:
        return FMT_LIST_SEPARATOR + FMT_LIST_SEPARATOR.join(unmanaged_files)
    return ''


def process():
    msg = next(api.consume(OutdatedKrb5conf), None)
    if not msg:
        raise StopActorExecutionError('Expected OutdatedKrb5conf, but got None')

    if msg.unmanaged_files:
        reporting.create_report([
            reporting.Title('Unmanaged MIT krb5 configuration file(s) will be '
                            'updated to point to the new X.509 CA bundle file'),
            reporting.Summary(
                'On RHEL 10, the location of the reference X.509 CA bundle '
                'file was modified. The following unmanaged MIT krb5 '
                'configuration files have to be updated to point to the new '
                'bundle file:' + __human_readable_list(msg.unmanaged_files)),
            reporting.Severity(reporting.Severity.INFO),
            reporting.Groups([reporting.Groups.SECURITY, reporting.Groups.AUTHENTICATION])
        ])

    if msg.rpm_provided_files:
        file_paths_from_rpm = [f'{r.path} (provided by {r.rpm})'for r in msg.rpm_provided_files]
        reporting.create_report([
            reporting.Title('RPM-provided MIT krb5 configuration file(s) are '
                            'pointing to outdated X.509 CA bundle file'),
            reporting.Summary(
                'On RHEL 10, the location of the reference X.509 CA bundle '
                'file was modified. Some MIT krb5 configuration files on this '
                'system are pointing to the old bundle file, but are provided '
                'by third-party RPMs. You must make sure these third-party '
                'RPMs were updated to reflect this change, or you may be '
                'unable to complete Kerberos PKINIT pre-authentication (e.g. '
                'using user certificates, or smartcards). The following files '
                'are affected:' + __human_readable_list(file_paths_from_rpm)),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups([reporting.Groups.SECURITY, reporting.Groups.AUTHENTICATION])
        ])

    if not msg.unmanaged_files and not msg.rpm_provided_files:
        api.current_logger().debug(
            'No outdated X.509 CA bundle references were found in MIT krb5 '
            'configuration files, thus these files will remain unchanged.'
        )
