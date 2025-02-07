from leapp.actors import Actor
from leapp.libraries.actor import convertkrb5conf
from leapp.models import OutdatedKrb5conf
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class ConvertKrb5conf(Actor):
    """
    Replace outdated references to the /etc/ssl/certs/ca-certificates.crt CA
    bundle by the new /etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem one in
    krb5 configuration files.
    """

    name = 'convert_krb5_conf'
    consumes = (OutdatedKrb5conf,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        convertkrb5conf.process()
