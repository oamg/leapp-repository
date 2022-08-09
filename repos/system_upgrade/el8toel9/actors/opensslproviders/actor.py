from leapp.actors import Actor
from leapp.libraries.actor import add_provider
from leapp.models import OpenSslConfig
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class OpenSslProviders(Actor):
    """
    Modify the openssl.cnf file to support new providers in OpenSSL 3.0

    Change the initialization:

    - openssl_conf = default_modules
    + openssl_conf = openssl_init

    Rename the default block and link the providers block:

    - [default_modules]
    + [openssl_init]
    + providers = provider_sect

    Add the providers block:

    + [provider_sect]
    + default = default_sect
    + ##legacy = legacy_sect
    +
    + [default_sect]
    + activate = 1
    +
    + ##[legacy_sect]
    + ##activate = 1
    """

    name = 'open_ssl_providers'
    consumes = (OpenSslConfig,)
    produces = ()
    tags = (IPUWorkflowTag, ApplicationsPhaseTag,)

    def process(self):
        add_provider.process(self.consume(OpenSslConfig))
