import os.path
import re
from collections import namedtuple

from leapp.libraries.actor import modscan
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import UpgradeDracutModule, RequiredUpgradeInitramPackages


def _files_get_folder_path(name):
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'files', name)
    assert os.path.isdir(path)
    return path


def test_created_modules(monkeypatch):
    monkeypatch.setattr(api, 'get_actor_folder_path', _files_get_folder_path)
    path = os.path.abspath(api.get_actor_folder_path('dracut'))
    required_modules = ['sys-upgrade', 'sys-upgrade-redhat']
    for mod in modscan._create_dracut_modules():
        index = required_modules.index(mod.name)

        # Ensures that this actor only includes known modules
        assert index != -1

        required_modules.pop(index)

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
    assert not required_modules


def test_required_packages(monkeypatch):
    # the default set of required rpms should not contain biosdevname
    assert 'biosdevname' not in modscan._REQUIRED_PACKAGES

    # for non-intel archs, the set of required rpms should be same as the default
    # one
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(architecture, 'matches_architecture', lambda x: False)
    assert set(modscan._REQUIRED_PACKAGES) == set(modscan._create_initram_packages().packages)

    monkeypatch.setattr(architecture, 'matches_architecture', lambda x: True)
    assert set(modscan._REQUIRED_PACKAGES + ['biosdevname']) == set(modscan._create_initram_packages().packages)


def test_process_produces_modules(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    messages = []
    monkeypatch.setattr(api, 'produce', lambda *x: messages.extend(x))
    monkeypatch.setattr(api, 'get_actor_folder_path', _files_get_folder_path)
    modscan.process()
    assert messages
    assert len(messages) == 3
    assert len([msg for msg in messages if isinstance(msg, UpgradeDracutModule)]) == 2
    assert len([msg for msg in messages if isinstance(msg, RequiredUpgradeInitramPackages)]) == 1
