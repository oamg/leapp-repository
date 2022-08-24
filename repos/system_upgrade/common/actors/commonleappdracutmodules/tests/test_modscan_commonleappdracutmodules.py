import os.path
import re
from collections import namedtuple

import pytest

from leapp.libraries.actor import modscan
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.utils.deprecation import suppress_deprecation

from leapp.models import (  # isort:skip
    RequiredUpgradeInitramPackages,  # deprecated
    UpgradeDracutModule,  # deprecated
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks
)


def _files_get_folder_path(name):
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'files', name)
    assert os.path.isdir(path)
    return path


@suppress_deprecation(UpgradeDracutModule)
def test_created_modules(monkeypatch):
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
    # the default set of required rpms should not contain biosdevname
    for pkg in ['biosdevname', 'policycoreutils', 'rng-tools']:
        assert pkg not in modscan._REQUIRED_PACKAGES

    required_packages = modscan._REQUIRED_PACKAGES[:]
    if dst_ver[0] == '9':
        required_packages += ['policycoreutils', 'rng-tools']
    if arch == architecture.ARCH_X86_64:
        required_packages += ['biosdevname']

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver=src_ver, dst_ver=dst_ver, arch=arch))
    old_initram, new_initram = modscan._create_initram_packages()
    assert (set(required_packages)
            == set(old_initram.packages)
            == set(new_initram.install_rpms))


@suppress_deprecation(UpgradeDracutModule)
def test_process_produces_modules(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
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
