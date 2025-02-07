from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import OutdatedKrb5confLocation


def _convert_krb5conf(conf_file):
    with open(conf_file) as f:
        text = f.read().replace('/etc/ssl/certs/ca-certificates.crt',
                                '/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem')
    with open(conf_file, 'w') as f:
        f.write(text)


def process():
    msg = next(api.consume(OutdatedKrb5confLocation), None)
    if not msg:
        api.current_logger().error(
            'Expected OutdatedKrb5confLocation, but got None. '
            'Cannot apply possibly needed changes in kerberos configuration files.'
        )
        return

    if msg.locations:
        for location in msg.locations:
            _convert_krb5conf(location)
