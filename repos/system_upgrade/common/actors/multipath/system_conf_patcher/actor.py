from leapp.actors import Actor
from leapp.libraries.actor import system_config_patcher
from leapp.models import MultipathConfigUpdatesInfo
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class MultipathSystemConfigPatcher(Actor):
    """
    Propagate any modified multipath configs to the source system.

    We copy, modify and use multipath configs from the source system in the upgrade initramfs
    as the configs might be incompatible with the target system. Once the upgrade is performed,
    actual system's configs need to be modified in the same fashion. This is achieved by simply
    copying our modified multipath configs that were used to upgrade the system.
    """

    name = 'multipath_system_config_patcher'
    consumes = (MultipathConfigUpdatesInfo,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        system_config_patcher.patch_system_configs()
