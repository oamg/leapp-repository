from leapp.actors import Actor
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import CopyFile, DistributionSignedRPM, TargetUserSpacePreupgradeTasks
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag

PLUGIN_PKGNAME = "kpatch-dnf"
CONFIG_PATH = "/etc/dnf/plugins/kpatch.conf"


class CheckKpatch(Actor):
    """
    Carry over kpatch-dnf and it's config into the container

    Check is kpatch-dnf plugin is installed and if it is, install it and copy
    over the config file so that the plugin can make a decision on whether any
    kpatch-patch packages need to be installed during in-place upgrade.
    """

    name = 'check_kpatch'
    consumes = (DistributionSignedRPM,)
    produces = (TargetUserSpacePreupgradeTasks,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        if has_package(DistributionSignedRPM, PLUGIN_PKGNAME):
            api.produce(TargetUserSpacePreupgradeTasks(
                install_rpms=[PLUGIN_PKGNAME],
                copy_files=[CopyFile(src=CONFIG_PATH)]))
