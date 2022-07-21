from leapp.actors import Actor
from leapp.libraries.actor.sssd_cache_files import remove_sssd_cache_files
from leapp.models import SSSDConfig
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class SSSDHandleCacheFiles(Actor):
    """
    If an SSSD configuration has been detected, special handling for SSSD cache files will be scheduled.

    After the upgrade from EL7 to EL8, SSSD isn't able to start anymore because the cache files have a newer
    format in RHEL7.9 than in RHEL8. This is a workaround for this issue.
    """

    name = 'sssd_handle_cache_files'
    consumes = (SSSDConfig,)
    produces = ()
    tags = (IPUWorkflowTag, ApplicationsPhaseTag)

    def process(self):
        remove_sssd_cache_files(
            next(self.consume(SSSDConfig), None)
        )
