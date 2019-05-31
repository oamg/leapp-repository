import base64
import io
import os
from subprocess import CalledProcessError
import tarfile

from leapp.libraries.common import reporting
from leapp.libraries.stdlib import api, run
from leapp.models import NtpMigrationDecision


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

    if len(migrate_configs):
        reporting.report_generic(
             title='{} configuration will be migrated'.format(' and '.join(migrate_configs)),
             summary='{} service(s) detected to be enabled and active'.format(', '.join(migrate_services)),
             severity='low')
        # Save configuration files that will be renamed in the upgrade
        config_tgz64 = get_tgz64(['/etc/ntp.conf', '/etc/ntp/keys',
                                  '/etc/ntp/crypto/pw', '/etc/ntp/step-tickers'])
    else:
        api.current_logger().info('ntpd/ntpdate configuration will not be migrated')
        migrate_services = []
        config_tgz64 = ''

    return NtpMigrationDecision(migrate_services=migrate_services, config_tgz64=config_tgz64)
