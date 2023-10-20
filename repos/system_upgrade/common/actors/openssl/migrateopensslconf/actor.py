from leapp.actors import Actor
from leapp.libraries.actor import migrateopensslconf
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class MigrateOpenSslConf(Actor):
    """
    Enforce the target default configuration file to be used.

    If the /etc/pki/tls/openssl.cnf has been modified and openssl.cnf.rpmnew
    file is created, backup the original one and replace it by the new default.

    tl;dr: (simplified)
    if the file is modified; then
      mv /etc/pki/tls/openssl.cnf{,.leappsave}
      mv /etc/pki/tls/openssl.cnf{.rpmnew,}
    fi
    """

    name = 'migrate_openssl_conf'
    consumes = ()
    produces = ()
    tags = (IPUWorkflowTag, ApplicationsPhaseTag)

    def process(self):
        migrateopensslconf.process()
