from leapp.actors import Actor
from leapp.libraries.actor import persistentnetnamesconfig
from leapp.models import (
    PersistentNetNamesFacts,
    PersistentNetNamesFactsInitramfs,
    RenamedInterfaces,
    TargetInitramfsTasks
)
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag
from leapp.utils.deprecation import suppress_deprecation


@suppress_deprecation(RenamedInterfaces)
class PersistentNetNamesConfig(Actor):
    """
    Generate udev persistent network naming configuration

    NOTE: This actor is deprecated and currently performs described actions
          only if LEAPP_NO_NETWORK_RENAMING != 1 and LEAPP_DISABLE_NET_NAMING_SCHEMES == 1.

    This actor generates systemd-udevd link files for each physical network
    interface present on the original system if the interface name differs
    on the target OS. Link file configuration will assign original name that has
    been detected on the source OS.

    Also produce list of interfaces which changed names during the upgrade
    process.
    """

    name = 'persistentnetnamesconfig'
    consumes = (PersistentNetNamesFacts, PersistentNetNamesFactsInitramfs)
    produces = (RenamedInterfaces, TargetInitramfsTasks)
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        persistentnetnamesconfig.process()
