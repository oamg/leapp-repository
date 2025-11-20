import shutil

from leapp.libraries.actor import system_config_patcher
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import TargetUserSpaceInfo, UpdatedMultipathConfig


def test_config_patcher(monkeypatch):
    modified_configs = [
        UpdatedMultipathConfig(path='/etc/multipath.conf'),
        UpdatedMultipathConfig(path='/etc/multipath/conf.d/myconfig.conf')
    ]

    target_uspace_info = TargetUserSpaceInfo(path='/uspace', scratch='', mounts='')
    actor_mock = CurrentActorMocked(msgs=modified_configs + [target_uspace_info])
    monkeypatch.setattr(api, 'current_actor', actor_mock)

    copies_performed = []

    def copy_mock(src, dst, *args, **kwargs):
        copies_performed.append((src, dst))

    monkeypatch.setattr(shutil, 'copy', copy_mock)
    system_config_patcher.patch_system_configs()

    expected_copies = [
        ('/uspace/etc/multipath.conf', '/etc/multipath.conf'),
        ('/uspace/etc/multipath/conf.d/myconfig.conf', '/etc/multipath/conf.d/myconfig.conf')
    ]

    assert sorted(copies_performed) == expected_copies
