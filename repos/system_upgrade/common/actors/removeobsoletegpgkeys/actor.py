from leapp.actors import Actor
from leapp.libraries.actor import removeobsoleterpmgpgkeys
from leapp.models import DNFWorkaround, InstalledRPM
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class RemoveObsoleteGpgKeys(Actor):
    """
    Remove obsoleted RPM GPG keys.

    The definition of what keys are considered obsolete depends on whether the
    upgrade also does a conversion:
    - If not converting, the obsolete keys are those that are no longer valid
      on the target version. This might be caused for example by the hashing
      algorithm becoming deprecated or by the key getting replaced. Note that
      only keys provided by the vendor of the OS are handled.
    - If converting, the obsolete keys are all of the keys provided by the
      vendor of the source distribution.

    A DNFWorkaround is registered to actually remove the keys.
    """

    name = "remove_obsolete_gpg_keys"
    consumes = (InstalledRPM,)
    produces = (DNFWorkaround,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        removeobsoleterpmgpgkeys.process()
