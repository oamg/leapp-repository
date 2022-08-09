from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor.opensslconfigcheck import (
    check_crypto_policies,
    check_default_modules,
    check_duplicate_extensions,
    check_min_max_protocol
)
from leapp.libraries.stdlib import api
from leapp.models import OpenSslConfig, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class OpenSslConfigCheck(Actor):
    """
    The OpenSSL configuration changed between RHEL8 and RHEL9 significantly with the rebase to
    OpenSSL 3.0. There are several things to check:

     * If the file was not modified by user, the RPM will take care of the upgrade
     * The file was modified and for some reason the link to the system-wide crypto
       policies is missing -- this is not recommended so we should warn users about that
     * The new OpenSSL 3.0 is using providers so we need to add them to the configuration
       file to make sure they behave the same way as when the original configuration file
       is used, especially for FIPS mode.
    """

    name = 'open_ssl_config_check'
    consumes = (OpenSslConfig,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag,)

    def process(self):
        openssl_messages = self.consume(OpenSslConfig)
        config = next(openssl_messages, None)
        if list(openssl_messages):
            api.current_logger().warning('Unexpectedly received more than one OpenSslConfig message.')
        if not config:
            raise StopActorExecutionError(
                'Could not check openssl configuration', details={'details': 'No OpenSslConfig facts found.'}
            )

        # If the configuration file was not modified, the rpm update will bring the new
        # changes by itself
        if not config.modified:
            return

        # Missing crypto policies is not recommended
        check_crypto_policies(config)

        # MinProtocol and MaxProtocol in [tls_system_default] changed their meaning
        check_min_max_protocol(config)

        # If the configuration file contains several X509 extensions with the same name,
        # only the last one will be used.
        check_duplicate_extensions(config)

        # Check and report what we are going to rewrite.
        #
        # Change the initialization:
        #
        # - openssl_conf = default_modules
        # + openssl_conf = openssl_init
        #
        # Rename the default block and link the providers block:
        #
        # - [default_modules]
        # + [openssl_init]
        # + providers = provider_sect
        #
        # Add the providers block:
        #
        # + [provider_sect]
        # + default = default_sect
        # + ##legacy = legacy_sect
        # +
        # + [default_sect]
        # + activate = 1
        # +
        # + ##[legacy_sect]
        # + ##activate = 1
        check_default_modules(config)
