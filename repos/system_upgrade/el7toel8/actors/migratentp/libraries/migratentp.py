import base64
import io
import tarfile

from leapp.exceptions import StopActorExecutionError
from leapp import reporting
from leapp.libraries.stdlib import CalledProcessError, run


COMMON_REPORT_GROUPS = [reporting.Groups.SERVICES, reporting.Groups.TIME_MANAGEMENT]


def extract_tgz64(s):
    stream = io.BytesIO(base64.b64decode(s))
    tar = tarfile.open(fileobj=stream, mode='r:gz')
    tar.extractall('/')
    tar.close()


def enable_service(name):
    try:
        run(['systemctl', 'enable', '{}.service'.format(name)])
    except CalledProcessError:
        raise StopActorExecutionError('Could not enable {} service'.format(name))


def write_file(name, content):
    with open(name, 'w') as f:
        f.write(content)


def ntp2chrony(root, ntp_conf, step_tickers):
    # need to skip these on pylint to avoid "function already defined" if we move to the top of file
    from leapp.libraries.actor import ntp2chrony  # pylint: disable=import-outside-toplevel

    try:
        ntp_configuration = ntp2chrony.NtpConfiguration(root, ntp_conf, step_tickers)
        ntp_configuration.write_chrony_configuration('/etc/chrony.conf', '/etc/chrony.keys',
                                                     False, True)
    except Exception as e:
        raise StopActorExecutionError('ntp2chrony failed: {}'.format(e))

    # Return ignored lines from ntp.conf, except 'disable monitor' from
    # the default ntp.conf
    return set(ntp_configuration.ignored_lines) - set(['disable monitor'])


def migrate_ntp(migrate_services, config_tgz64):
    # Map of ntp->chrony services and flag if using configuration
    service_map = {'ntpd': ('chronyd', True),
                   'ntpdate': ('chronyd', True),
                   'ntp-wait': ('chrony-wait', False)}

    # Minimal secure ntp.conf with no sources to migrate ntpdate only
    no_sources_directives = (
            '# This file was created to migrate ntpdate configuration to chrony\n'
            '# without ntp configuration (ntpd service was disabled)\n'
            'driftfile /var/lib/ntp/drift\n'
            'restrict default ignore nomodify notrap nopeer noquery\n')

    if not migrate_services:
        # Nothing to migrate
        return

    migrate_configs = []
    for service in migrate_services:
        if service not in service_map:
            raise StopActorExecutionError('Unknown service {}'.format(service))
        enable_service(service_map[service][0])
        if service_map[service][1]:
            migrate_configs.append(service)

    # Unpack archive with configuration files
    extract_tgz64(config_tgz64)

    if 'ntpd' in migrate_configs:
        ntp_conf = '/etc/ntp.conf'
    else:
        ntp_conf = '/etc/ntp.conf.nosources'
        write_file(ntp_conf, no_sources_directives)

    step_tickers = '/etc/ntp/step-tickers' if 'ntpdate' in migrate_configs else ''

    ignored_lines = ntp2chrony('/', ntp_conf, step_tickers)

    config_resources = [reporting.RelatedResource('file', mc) for mc in migrate_configs + [ntp_conf]]
    package_resources = [reporting.RelatedResource('package', p) for p in ['ntpd', 'chrony']]

    if not ignored_lines:
        reporting.create_report([
            reporting.Title('{} configuration migrated to chrony'.format(' and '.join(migrate_configs))),
            reporting.Summary('ntp2chrony executed successfully'),
            reporting.Severity(reporting.Severity.INFO),
            reporting.Groups(COMMON_REPORT_GROUPS)
        ] + config_resources + package_resources)

    else:
        reporting.create_report([
            reporting.Title('{} configuration partially migrated to chrony'.format(' and '.join(migrate_configs))),
            reporting.Summary('Some lines in /etc/ntp.conf were ignored in migration (check /etc/chrony.conf)'),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups(COMMON_REPORT_GROUPS)
        ] + config_resources + package_resources)
