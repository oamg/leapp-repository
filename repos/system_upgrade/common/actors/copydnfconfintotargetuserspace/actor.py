from leapp.actors import Actor
from leapp.libraries.actor import copydnfconfintotargetuserspace
from leapp.models import TargetUserSpacePreupgradeTasks
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class CopyDNFConfIntoTargetUserspace(Actor):
    """
    Copy dnf.conf into target userspace

    Copies /etc/leapp/files/dnf.conf to target userspace. If it isn't available
    /etc/dnf/dnf.conf is copied instead. This allows specifying a different
    config for the target userspace, which might be required if the source
    system configuration file isn't compatible with the target one. One such
    example is incompatible proxy configuration between RHEL7 and RHEL8 DNF
    versions.
    """
    name = "copy_dnf_conf_into_target_userspace"
    consumes = ()
    produces = (TargetUserSpacePreupgradeTasks,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        copydnfconfintotargetuserspace.process()
