import base64
import io
import os
import tarfile

from leapp import reporting
from leapp.libraries.stdlib import CalledProcessError, api, run
from leapp.models import NtpMigrationDecision


files = [
    '/etc/ntp.conf', '/etc/ntp/keys',
    '/etc/ntp/crypto/pw', '/etc/ntp/step-tickers'
]

related = [
    reporting.RelatedResource('package', 'ntpd'),
    reporting.RelatedResource('package', 'chrony'),
] + [reporting.RelatedResource('file', f) for f in files]


# Check if a service is active and enabled
def check_service(name):
    for state in ['active', 'enabled']:
        try:
            run(['systemctl', 'is-{}'.format(state), name])
            api.current_logger().debug('{} is {}'.format(name, state))
        except CalledProcessError:
            api.current_logger().debug('{} is not {}'.format(name, state))
            return False

    return True


# Check if a file exists
def is_file(name):
    return os.path.isfile(name)


# Get a base64-encoded gzipped tarball of specified files
def get_tgz64(filenames):
    stream = io.BytesIO()
    tar = tarfile.open(fileobj=stream, mode='w:gz')
    for filename in filenames:
        if os.path.isfile(filename):
            tar.add(filename)
    tar.close()

    return base64.b64encode(stream.getvalue())


# Check services from the ntp packages for migration
def check_ntp(installed_packages):
    service_data = [('ntpd', 'ntp', '/etc/ntp.conf'),
                    ('ntpdate', 'ntpdate', '/etc/ntp/step-tickers'),
                    ('ntp-wait', 'ntp-perl', None)]

    migrate_services = []
    migrate_configs = []
    for service, package, main_config in service_data:
        if package in installed_packages and \
                check_service('{}.service'.format(service)) and \
                (not main_config or is_file(main_config)):
            migrate_services.append(service)
            if main_config:
                migrate_configs.append(service)

    if migrate_configs:
        reporting.create_report([
            reporting.Title('{} configuration will be migrated'.format(' and '.join(migrate_configs))),
            reporting.Summary('{} service(s) detected to be enabled and active'.format(', '.join(migrate_services))),
            reporting.Severity(reporting.Severity.LOW),
            reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.TIME_MANAGEMENT]),
        ] + related)

        # Save configuration files that will be renamed in the upgrade
        config_tgz64 = get_tgz64(files)
    else:
        api.current_logger().info('ntpd/ntpdate configuration will not be migrated')
        migrate_services = []
        config_tgz64 = ''

    return NtpMigrationDecision(migrate_services=migrate_services, config_tgz64=config_tgz64)
