from leapp.actors import Actor
from leapp.libraries.actor import removeobsoleterpmgpgkeys
from leapp.models import DNFWorkaround, InstalledRPM
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class RemoveObsoleteGpgKeys(Actor):
    """
    Remove obsoleted RPM GPG keys.

    New version might make existing RPM GPG keys obsolete. This might be caused
    for example by the hashing algorithm becoming deprecated or by the key
    getting replaced.

    A DNFWorkaround is registered to actually remove the keys.
    """

    name = "remove_obsolete_gpg_keys"
    consumes = (InstalledRPM,)
    produces = (DNFWorkaround,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        removeobsoleterpmgpgkeys.process()
