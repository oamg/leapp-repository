import os
import re

from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import RequiredUpgradeInitramPackages, UpgradeDracutModule

_REQUIRED_PACKAGES = [
    'binutils',
    'cifs-utils',
    'device-mapper-multipath',
    'dracut',
    'dracut-config-generic',
    'dracut-config-rescue',
    'dracut-network',
    'dracut-tools',
    'fcoe-utils',
    'hostname',
    'iscsi-initiator-utils',
    'kbd',
    'kernel',
    'kernel-core',
    'kernel-modules',
    'keyutils',
    'lldpad',
    'lvm2',
    'mdadm',
    'nfs-utils',
    'openssh-clients',
    'plymouth',
    'rpcbind',
    'systemd-container',
    'tar'
]


def _create_dracut_modules():
    dracut_base_path = api.get_actor_folder_path('dracut')
    if dracut_base_path:
        dracut_base_path = os.path.abspath(dracut_base_path)
        for module in os.listdir(dracut_base_path):
            yield UpgradeDracutModule(
                name=re.sub(r'^\d+', '', module),
                module_path=os.path.join(dracut_base_path, module)
            )


def _create_initram_packages():
    required_pkgs = _REQUIRED_PACKAGES
    if architecture.matches_architecture(architecture.ARCH_X86_64):
        required_pkgs.append('biosdevname')
    return RequiredUpgradeInitramPackages(packages=required_pkgs)


def process():
    api.produce(*tuple(_create_dracut_modules()))
    api.produce(_create_initram_packages())
