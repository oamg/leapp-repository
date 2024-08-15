import sys
from collections import namedtuple
from enum import Enum

import pytest

import leapp.libraries.actor.scan_livemode_config as scan_livemode_config_lib
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import LiveModeConfig

try:
    import configparser
except ImportError:
    import ConfigParser as configparser


class EnablementResult(Enum):
    DO_NOTHING = 0
    RAISE = 1
    SCAN_CONFIG = 2


EnablementTestCase = namedtuple('EnablementTestCase', ('env_vars', 'arch', 'pkgs', 'result'))


@pytest.mark.parametrize(
    'case_descr',
    (
        EnablementTestCase(env_vars={'LEAPP_UNSUPPORTED': '1', 'LEAPP_DEVEL_ENABLE_LIVE_MODE': '1'},
                           arch=architecture.ARCH_X86_64, pkgs=('squashfs-tools', ),
                           result=EnablementResult.SCAN_CONFIG),
        EnablementTestCase(env_vars={'LEAPP_UNSUPPORTED': '0', 'LEAPP_DEVEL_ENABLE_LIVE_MODE': '1'},
                           arch=architecture.ARCH_X86_64, pkgs=('squashfs-tools', ),
                           result=EnablementResult.DO_NOTHING),
        EnablementTestCase(env_vars={'LEAPP_UNSUPPORTED': '1', 'LEAPP_DEVEL_ENABLE_LIVE_MODE': '0'},
                           arch=architecture.ARCH_X86_64, pkgs=('squashfs-tools', ),
                           result=EnablementResult.DO_NOTHING),
        EnablementTestCase(env_vars={'LEAPP_UNSUPPORTED': '1', 'LEAPP_DEVEL_ENABLE_LIVE_MODE': '1'},
                           arch=architecture.ARCH_ARM64, pkgs=('squashfs-tools', ),
                           result=EnablementResult.RAISE),
        EnablementTestCase(env_vars={'LEAPP_UNSUPPORTED': '1', 'LEAPP_DEVEL_ENABLE_LIVE_MODE': '1'},
                           arch=architecture.ARCH_ARM64, pkgs=tuple(),
                           result=EnablementResult.RAISE),
    )
)
def test_enablement_conditions(monkeypatch, case_descr):
    """
    Check whether scanning is performed only when enablement and system conditions are met.

    Enablement conditions:
    - LEAPP_UNSUPPORTED=1
    - LEAPP_DEVEL_ENABLE_LIVE_MODE=1

    Not meeting enablement conditions should prevent config message from being produced.

    System requirements:
    - architecture = x86_64
    - 'squashfs-tools' package is installed

    Not meeting system requirements should raise StopActorExecutionError.
    """

    def has_package_mock(message_class, pkg_name):
        return pkg_name in case_descr.pkgs

    monkeypatch.setattr(scan_livemode_config_lib, 'has_package', has_package_mock)

    mocked_actor = CurrentActorMocked(envars=case_descr.env_vars, arch=case_descr.arch)
    monkeypatch.setattr(api, 'current_actor', mocked_actor)

    if case_descr.result == EnablementResult.RAISE:
        with pytest.raises(StopActorExecutionError):
            scan_livemode_config_lib.should_scan_config()
    else:
        should_scan = scan_livemode_config_lib.should_scan_config()

        if case_descr.result == EnablementResult.DO_NOTHING:
            assert not should_scan
        elif case_descr.result == EnablementResult.SCAN_CONFIG:
            assert should_scan


def test_config_scanning(monkeypatch):
    """ Test whether scanning a valid config is properly transcribed into a config message. """

    config_lines = [
        '[livemode]',
        'squashfs_fullpath=IMG',
        'setup_network_manager=yes',
        'autostart_upgrade_after_reboot=no',
        'setup_opensshd_with_auth_keys=/root/.ssh/authorized_keys',
        'setup_passwordless_root=no',
        'additional_packages=pkgA,pkgB'
    ]
    config_content = '\n'.join(config_lines) + '\n'

    if sys.version[0] == '2':
        config_content = config_content.decode('utf-8')  # python2 compat

    class ConfigParserMock(configparser.ConfigParser):  # pylint: disable=too-many-ancestors
        def read(self, file_paths, *args, **kwargs):
            self.read_string(config_content)
            return file_paths

    monkeypatch.setattr(configparser, 'ConfigParser', ConfigParserMock)

    monkeypatch.setattr(scan_livemode_config_lib, 'should_scan_config', lambda: True)

    monkeypatch.setattr(api, 'produce', produce_mocked())

    scan_livemode_config_lib.scan_config_and_emit_message()

    assert api.produce.called
    assert len(api.produce.model_instances) == 1

    produced_message = api.produce.model_instances[0]
    assert isinstance(produced_message, LiveModeConfig)

    assert produced_message.additional_packages == ['pkgA', 'pkgB']
    assert produced_message.squashfs_fullpath == 'IMG'
    assert produced_message.setup_opensshd_with_auth_keys == '/root/.ssh/authorized_keys'
    assert produced_message.setup_network_manager
