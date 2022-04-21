from leapp.actors import Actor
from leapp.libraries.actor import migrateblacklistca
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class MigrateBlacklistCA(Actor):
    """
    Preserve blacklisted certificates during the upgrade

    Path for the blacklisted certificates has been changed on RHEL 9.
    The original paths on RHEL 8 and older systems have been:
        /etc/pki/ca-trust/source/blacklist/
        /usr/share/pki/ca-trust-source/blacklist/
    However on RHEL 9 the blacklist directory has been renamed to 'blocklist'.
    So the new paths are:
        /etc/pki/ca-trust/source/blocklist/
        /usr/share/pki/ca-trust-source/blocklist/
    This actor moves all blacklisted certificates into the expected directories
    and fix symlinks if needed.
    """

    name = 'migrate_blacklist_ca'
    consumes = ()
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        migrateblacklistca.process()
