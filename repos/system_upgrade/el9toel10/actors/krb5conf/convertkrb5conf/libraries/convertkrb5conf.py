from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import OutdatedKrb5conf


def _backup_krb5conf(conf_file):
    try:
        run(['/usr/bin/cp', conf_file, conf_file + '.leappsave'])
    except CalledProcessError:
        return False
    return True

def _convert_krb5conf(conf_file):
    with open(conf_file) as f:
        text = f.read().replace('/etc/ssl/certs/ca-certificates.crt',
                                '/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem')
    with open(conf_file, 'w') as f:
        f.write(text)


def process():
    msg = next(api.consume(OutdatedKrb5conf), None)
    if not msg:
        api.current_logger().error(
            'Expected OutdatedKrb5conf, but got None. '
            'Cannot apply possibly needed changes in kerberos configuration files.'
        )
        return

    if msg.unmanaged_files:
        for file_path in msg.unmanaged_files:
            if not _backup_krb5conf(file_path):
                api.current_logger().error(
                    f'Could not back up the {file_path} file. Skipping other actions.'
                )
                return
            _convert_krb5conf(file_path)
