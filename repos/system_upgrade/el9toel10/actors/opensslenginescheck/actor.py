from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor.opensslenginescheck import check_openssl_engines
from leapp.libraries.stdlib import api
from leapp.models import OpenSslConfig, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class OpenSslEnginesCheck(Actor):
    """
    The OpenSSL in RHEL 10 has deprecated engines in favor of providers.

    When they are kept in the default configuration file, they might
    not work as expected.

     * The most common engine we shipped, pkcs11, has been removed from RHEL 10,
       which might cause failures to load the OpenSSL if it is hardcoded in the
       configuration file. However, as far as the /etc/pki/tls/openssl.cnf
       configuration file is replaced during the upgrade by the target default
       configuration, it should be ok to just inform user about that (see
       related actors in the system_upgrade_common repository).
     * Similarly user should be warned in case of third-party engines
    """

    name = 'open_ssl_engines_check'
    consumes = (OpenSslConfig,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag,)

    def process(self):
        openssl_messages = self.consume(OpenSslConfig)
        config = next(openssl_messages, None)
        if list(openssl_messages):
            api.current_logger().warning('Unexpectedly received more than one OpenSslConfig message.')
        if not config:
            # NOTE: unexpected situation - putting the check just as a seatbelt
            # - not covered by unit-tests.
            raise StopActorExecutionError(
                'Could not check openssl configuration', details={'details': 'No OpenSslConfig facts found.'}
            )

        # If the configuration file was not modified, it can not contain user changes
        if not config.modified:
            return

        # The libp11 documentation has the following configuration snippet in the README:
        #
        #   [openssl_init]
        #   engines=engine_section
        #
        #   [engine_section]
        #   pkcs11 = pkcs11_section
        #
        #   [pkcs11_section]
        #   engine_id = pkcs11
        #   dynamic_path = /usr/lib/ssl/engines/libpkcs11.so
        #   MODULE_PATH = opensc-pkcs11.so
        #   init = 0
        #
        # The `openssl_init` is  required by OpenSSL 3.0 so we need to explore the section
        # pointed out by the `engines` key in there
        check_openssl_engines(config)
