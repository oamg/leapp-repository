import shutil

from leapp.libraries.actor import system_config_patcher
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import UpdatedMultipathConfig


def test_config_patcher(monkeypatch):
    modified_configs = [
        UpdatedMultipathConfig(
            updated_config_location='/var/lib/leapp/planned_conf_modifications/etc/multipath.conf',
            target_path='/etc/multipath.conf'
        ),
        UpdatedMultipathConfig(
            updated_config_location='/var/lib/leapp/planned_conf_modifications/etc/multipath/conf.d/myconfig.conf',
            target_path='/etc/multipath/conf.d/myconfig.conf'
        )
    ]

    actor_mock = CurrentActorMocked(msgs=modified_configs)
    monkeypatch.setattr(api, 'current_actor', actor_mock)

    copies_performed = []

    def copy_mock(src, dst, *args, **kwargs):
        copies_performed.append((src, dst))

    monkeypatch.setattr(shutil, 'copy', copy_mock)
    system_config_patcher.patch_system_configs()

    expected_copies = [
        ('/var/lib/leapp/planned_conf_modifications/etc/multipath.conf', '/etc/multipath.conf'),
        (
            '/var/lib/leapp/planned_conf_modifications/etc/multipath/conf.d/myconfig.conf',
            '/etc/multipath/conf.d/myconfig.conf'
        )
    ]

    assert sorted(copies_performed) == expected_copies
