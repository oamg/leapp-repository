from leapp.actors import Actor
from leapp.libraries.actor import setetcreleasever
from leapp.models import PkgManagerInfo, RHUIInfo
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class SetEtcReleaseVer(Actor):
    """
    Release version in /etc/dnf/vars/releasever will be set to the current target release

    If Leapp detects "releasever" variable is either configured through DNF/YUM configuration
    file and/or the system is using RHUI infrastructure, release version will be set to the target
    release version in order to avoid issues with repofile URLs (when --release option is not provided)
    in cases where there is the previous major.minor version value in the configuration. This will also
    ensure the system stays on the target version after the upgrade.
    """

    name = 'set_etc_releasever'
    consumes = (PkgManagerInfo, RHUIInfo)
    produces = ()
    tags = (IPUWorkflowTag, ApplicationsPhaseTag)

    def process(self):
        setetcreleasever.process()
