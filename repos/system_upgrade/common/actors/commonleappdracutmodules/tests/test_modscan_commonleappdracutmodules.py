import os.path
import re
from collections import namedtuple

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import modscan
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.utils.deprecation import suppress_deprecation

from leapp.models import (  # isort:skip
    KernelInfo,
    RPM,
    RequiredUpgradeInitramPackages,  # deprecated
    UpgradeDracutModule,  # deprecated
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks
)

_KERNEL_INFO_4K = KernelInfo(
    pkg=RPM(name='kernel-core', arch='x86_64', version='5.14.0', release='100.el9',
            epoch='0', packager='', pgpsig='SIG'),
    type='ordinary',
    uname_r='5.14.0-100.el9.x86_64',
    page_size='4k',
)

_KERNEL_INFO_64K = KernelInfo(
    pkg=RPM(name='kernel-64k-core', arch='aarch64', version='5.14.0', release='100.el9',
            epoch='0', packager='', pgpsig='SIG'),
    type='ordinary',
    uname_r='5.14.0-100.el9.aarch64+64k',
    page_size='64k',
)

_KERNEL_INFO_64K_PPC = KernelInfo(
    pkg=RPM(name='kernel-core', arch='ppc64le', version='5.14.0', release='100.el9',
            epoch='0', packager='', pgpsig='SIG'),
    type='ordinary',
    uname_r='5.14.0-100.el9.ppc64le',
    page_size='64k',
)


def _files_get_folder_path(name):
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'files', name)
    assert os.path.isdir(path)
    return path


@suppress_deprecation(UpgradeDracutModule)
def test_created_modules(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    monkeypatch.setattr(api, 'get_actor_folder_path', _files_get_folder_path)
    path = os.path.abspath(api.get_actor_folder_path('dracut'))
    required_modules = {'sys-upgrade', 'sys-upgrade-redhat'}
    # _old is for deprecated stuff, _new is ...
    # we want to test that the new and original solution produce 'equivalent' output
    produced_required_modules_old = set()
    produced_required_modules_new = set()

    def check_module(mod):
        # Ensures that this actor only includes known modules
        assert mod.name in required_modules

        # Ensures that the path is valid
        assert mod.module_path
        assert mod.module_path == os.path.abspath(mod.module_path)

        # Ensure it's a directory
        assert os.path.isdir(mod.module_path)

        # Ensure it's located within the actors files path
        assert mod.module_path.startswith(path)

        # Ensure the directory name ends with the module name
        assert os.path.basename(mod.module_path).endswith(mod.name)
        assert not re.sub(r'^(85|90){}$'.format(mod.name), '', os.path.basename(mod.module_path))

    for msg in modscan._create_dracut_modules():
        if isinstance(msg, UpgradeDracutModule):
            produced_required_modules_old.add(msg.name)
            check_module(msg)
        else:
            for mod in msg.include_dracut_modules:
                produced_required_modules_new.add(mod.name)
                check_module(mod)

    # ensure that old and new solution produce equivalent (expected) output
    assert produced_required_modules_new == produced_required_modules_old == required_modules


@pytest.mark.parametrize('src_ver,dst_ver,arch', (
    ('7.9', '8.4', architecture.ARCH_X86_64),
    ('7.9', '8.4', architecture.ARCH_S390X),
    ('8.4', '9.0', architecture.ARCH_X86_64),
    ('8.4', '9.0', architecture.ARCH_S390X),
))
def test_required_packages(monkeypatch, src_ver, dst_ver, arch):
    for pkg in ['biosdevname', 'policycoreutils', 'rng-tools', 'kernel', 'kernel-core', 'kernel-modules']:
        assert pkg not in modscan._REQUIRED_PACKAGES

    required_packages = modscan._REQUIRED_PACKAGES[:]
    if dst_ver[0] == '9':
        required_packages += ['policycoreutils', 'rng-tools']
    if arch == architecture.ARCH_X86_64:
        required_packages += ['biosdevname']
    required_packages += ['kernel', 'kernel-core', 'kernel-modules']

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        src_ver=src_ver, dst_ver=dst_ver, arch=arch, msgs=[_KERNEL_INFO_4K]
    ))
    old_initram, new_initram = modscan._create_initram_packages()
    assert (set(required_packages)
            == set(old_initram.packages)
            == set(new_initram.install_rpms))


def test_required_packages_no_kernel_info(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='9.8', dst_ver='10.2'))
    with pytest.raises(StopActorExecutionError):
        modscan._create_initram_packages()


@pytest.mark.parametrize('kernel_info,arch,expected_kernel_pkgs,unexpected_kernel_pkgs', (
    (_KERNEL_INFO_4K, architecture.ARCH_ARM64,
     ['kernel', 'kernel-core', 'kernel-modules'],
     ['kernel-64k', 'kernel-64k-core', 'kernel-64k-modules']),
    (_KERNEL_INFO_64K, architecture.ARCH_ARM64,
     ['kernel-64k', 'kernel-64k-core', 'kernel-64k-modules'],
     ['kernel', 'kernel-core', 'kernel-modules']),
    # ppc64le: 64k page size but standard kernel packages (no kernel-64k RPMs)
    (_KERNEL_INFO_64K_PPC, architecture.ARCH_PPC64LE,
     ['kernel', 'kernel-core', 'kernel-modules'],
     ['kernel-64k', 'kernel-64k-core', 'kernel-64k-modules']),
    # x86_64: 4k page size, standard kernel packages
    (_KERNEL_INFO_4K, architecture.ARCH_X86_64,
     ['kernel', 'kernel-core', 'kernel-modules'],
     ['kernel-64k', 'kernel-64k-core', 'kernel-64k-modules']),
    # s390x: 4k page size, standard kernel packages
    (_KERNEL_INFO_4K, architecture.ARCH_S390X,
     ['kernel', 'kernel-core', 'kernel-modules'],
     ['kernel-64k', 'kernel-64k-core', 'kernel-64k-modules']),
))
def test_required_packages_page_size(monkeypatch, kernel_info, arch, expected_kernel_pkgs, unexpected_kernel_pkgs):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        src_ver='9.6', dst_ver='10.0', arch=arch, msgs=[kernel_info]
    ))
    old_initram, new_initram = modscan._create_initram_packages()
    for pkg in expected_kernel_pkgs:
        assert pkg in new_initram.install_rpms
        assert pkg in old_initram.packages
    for pkg in unexpected_kernel_pkgs:
        assert pkg not in new_initram.install_rpms
        assert pkg not in old_initram.packages


@suppress_deprecation(UpgradeDracutModule)
def test_process_produces_modules(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[_KERNEL_INFO_4K]))
    messages = []
    monkeypatch.setattr(api, 'produce', lambda *x: messages.extend(x))
    monkeypatch.setattr(api, 'get_actor_folder_path', _files_get_folder_path)
    modscan.process()
    assert messages
    assert len(messages) == 6
    assert len([msg for msg in messages if isinstance(msg, UpgradeDracutModule)]) == 2
    assert len([msg for msg in messages if isinstance(msg, UpgradeInitramfsTasks)]) == 2
    assert len([msg for msg in messages if isinstance(msg, RequiredUpgradeInitramPackages)]) == 1
    assert len([msg for msg in messages if isinstance(msg, TargetUserSpaceUpgradeTasks)]) == 1
