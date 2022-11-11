import os
import re

from leapp.libraries.common.config import architecture, version
from leapp.libraries.stdlib import api
from leapp.utils.deprecation import suppress_deprecation

from leapp.models import (  # isort:skip
    CopyFile,
    RequiredUpgradeInitramPackages,  # deprecated
    UpgradeDracutModule,  # deprecated
    DracutModule,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks
)

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


def _create_initram_networking_tasks():
    # include networking-related dracut modules
    modules_map = {'network-manager': ('network-manager', '/etc/leapp-initram-network-manager'),
                   'scripts': ('network', '/etc/leapp-initram-network-scripts')}
    initram_network_chosen = os.getenv('LEAPP_DEVEL_INITRAM_NETWORK', None)
    if initram_network_chosen in modules_map:
        module, touch_file = modules_map[initram_network_chosen]
        yield UpgradeInitramfsTasks(include_dracut_modules=[DracutModule(name=module)])
        # touch expected file
        yield TargetUserSpaceUpgradeTasks(copy_files=[CopyFile(src='/dev/null', dst=touch_file)])


# The decorator is not effective for generators, it has to be used one level
# above
# @suppress_deprecation(UpgradeDracutModule)
def _create_dracut_modules():
    dracut_base_path = api.get_actor_folder_path('dracut')
    if dracut_base_path:
        dracut_base_path = os.path.abspath(dracut_base_path)
        for module in os.listdir(dracut_base_path):
            yield UpgradeDracutModule(
                name=re.sub(r'^\d+', '', module),
                module_path=os.path.join(dracut_base_path, module)
            )
            # NOTE: when the UpgradeDracutModule is dropped, this could be
            # handled just by one msg instead of two
            dm = DracutModule(
                name=re.sub(r'^\d+', '', module),
                module_path=os.path.join(dracut_base_path, module))
            yield UpgradeInitramfsTasks(include_dracut_modules=[dm])


@suppress_deprecation(RequiredUpgradeInitramPackages)
def _create_initram_packages():
    # copy the list as we do not want to affect the constant because of tests
    required_pkgs = _REQUIRED_PACKAGES[:]
    if architecture.matches_architecture(architecture.ARCH_X86_64):
        required_pkgs.append('biosdevname')
    if os.getenv('LEAPP_DEVEL_INITRAM_NETWORK', None) == 'network-manager':
        required_pkgs.append('NetworkManager')
    if version.get_target_major_version() == '9':
        required_pkgs += ['policycoreutils', 'rng-tools']
    return (
        RequiredUpgradeInitramPackages(packages=required_pkgs),
        TargetUserSpaceUpgradeTasks(install_rpms=required_pkgs)
    )


def process():
    api.produce(*tuple(_create_dracut_modules()))
    api.produce(*_create_initram_packages())
    api.produce(*tuple(_create_initram_networking_tasks()))
