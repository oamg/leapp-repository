import os

from leapp.actors import Actor
from leapp.libraries.stdlib import api
from leapp.models import (
    LiveModeConfigFacts,
    LiveModeRequirementsTasks,
    RequiredUpgradeInitramPackages,
)
from leapp.tags import ExperimentalTag, InterimPreparationPhaseTag, IPUWorkflowTag
from leapp.utils.deprecation import suppress_deprecation

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
    consumes = (LiveModeConfigFacts,)
    produces = (LiveModeRequirementsTasks,)
    tags = (ExperimentalTag, InterimPreparationPhaseTag, IPUWorkflowTag,)

    @suppress_deprecation(RequiredUpgradeInitramPackages)
    def process(self):
        livemode = next(api.consume(LiveModeConfigFacts), None)
        if not livemode or not livemode.enabled:
            return

        packages = _REQUIRED_PACKAGES_FOR_LIVE_MODE + livemode.packages
        if livemode.authorized_keys:
            packages += ['openssh-server', 'crypto-policies']

        if api.current_actor().configuration.architecture == 'x86_64':
            packages += ['dmidecode', 'pciutils', 'lsscsi']

        if os.getenv('LEAPP_LIVE_SOSREPORT', 0):
            packages += ['sos']

        api.produce(RequiredUpgradeInitramPackages(packages=packages))
