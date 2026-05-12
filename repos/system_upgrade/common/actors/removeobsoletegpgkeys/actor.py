from leapp.actors import Actor
from leapp.configs.common.rhui import all_rhui_cfg
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

    Additionally, if RHUI configuration is active (use_config=True), GPG keys
    specified in the RHUI obsolete_gpg_keys configuration will also be removed.

    A DNFWorkaround is registered to actually remove the keys.
    """

    name = "remove_obsolete_gpg_keys"
    config_schemas = all_rhui_cfg
    consumes = (InstalledRPM,)
    produces = (DNFWorkaround,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        removeobsoleterpmgpgkeys.process()
