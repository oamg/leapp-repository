import base64
import io
import tarfile

from leapp.libraries.stdlib import api, CalledProcessError, run


def extract_tgz64(s):
    stream = io.BytesIO(base64.b64decode(s))
    tar = tarfile.open(fileobj=stream, mode='r:gz')
    tar.extractall('/')
    tar.close()


def enable_service(name):
    try:
        run(['systemctl', 'enable', '{}.service'.format(name)])
    except CalledProcessError:
        api.current_logger().error('Could not enable {} service'.format(name))


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
    except OSError as e:
        api.current_logger().error('ntp2chrony failed: {}'.format(e))
        return False, set()

    # Return ignored lines from ntp.conf, except 'disable monitor' from
    # the default ntp.conf
    return True, set(ntp_configuration.ignored_lines) - set(['disable monitor'])


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
            api.current_logger().error('Unknown service {}'.format(service))
            continue
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

    conf_migrated, ignored_lines = ntp2chrony('/', ntp_conf, step_tickers)

    if conf_migrated:
        api.current_logger().info('Configuration files migrated to chrony: {}'.format(' '.join(migrate_configs)))
        if ignored_lines:
            api.current_logger().warning('Some lines in /etc/ntp.conf were ignored in migration'
                                         ' (check /etc/chrony.conf)')
