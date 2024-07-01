import os

from leapp.actors import Actor
from leapp.libraries.common import dnfplugin
from leapp.libraries.stdlib import api
from leapp.models import LiveModeConfigFacts, LiveModeRequirementsTasks, TargetUserSpaceInfo, UsedTargetRepositories
from leapp.tags import ExperimentalTag, InterimPreparationPhaseTag, IPUWorkflowTag

# NOTE: would also need
# _REQUIRED_PACKAGES from actors/commonleappdracutmodules/libraries/modscan.py

_REQUIRED_PACKAGES_FOR_LIVE_MODE = [
    'systemd-container',
    'dbus-daemon',
    'NetworkManager',
    'util-linux',
    'dracut-live',
    'dracut-squash',
    'passwd',
    'kexec-tools',
    'vi',
    'less',
    'openssh-clients',
    'strace',
    'tcpdump',
]


class PrepareLiveRequirements(Actor):
    """
    Install the needful to build a live squashfs image
    -> dracut-live, dracut-squash and a few debug tools.
    """

    name = 'prepare_live_requirements'
    consumes = (LiveModeConfigFacts,
                TargetUserSpaceInfo,
                UsedTargetRepositories)
    produces = (LiveModeRequirementsTasks)
    tags = (ExperimentalTag, InterimPreparationPhaseTag, IPUWorkflowTag,)

    def process(self):
        livemode = next(api.consume(LiveModeConfigFacts), None)
        if not livemode or not livemode.enabled:
            return

        userspace_info = next(api.consume(TargetUserSpaceInfo), None)
        used_repos = api.consume(UsedTargetRepositories)

        packages = _REQUIRED_PACKAGES_FOR_LIVE_MODE + livemode.packages
        if livemode.authorized_keys:
            packages += ['openssh-server', 'crypto-policies']

        if api.current_actor().configuration.architecture == 'x86_64':
            packages += ['dmidecode', 'pciutils', 'lsscsi']

        if os.getenv('LEAPP_LIVE_SOSREPORT', 0):
            packages += ['sos']

        dnfplugin.install_initramdisk_requirements(
            packages=packages,
            target_userspace_info=userspace_info,
            used_repos=used_repos)

        api.produce(LiveModeRequirementsTasks(packages=packages))
