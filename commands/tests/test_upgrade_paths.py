import mock
import pytest

from leapp.cli.commands import command_utils
from leapp.exceptions import CommandError


@mock.patch("leapp.cli.commands.command_utils.get_upgrade_paths_config",
            return_value={"default": {"7.9": ["8.4"], "8.6": ["9.0"], "7": ["8.4"], "8": ["9.0"]}})
def test_get_target_version(mock_open, monkeypatch):

    monkeypatch.setattr(command_utils, 'get_os_release_version_id', lambda x: '8.6')
    assert command_utils.get_target_version('default') == '9.0'

    monkeypatch.setenv('LEAPP_DEVEL_TARGET_RELEASE', '')
    monkeypatch.setattr(command_utils, 'get_os_release_version_id', lambda x: '8.6')
    assert command_utils.get_target_version('default') == '9.0'

    monkeypatch.delenv('LEAPP_DEVEL_TARGET_RELEASE', raising=True)
    # unsupported path
    monkeypatch.setattr(command_utils, 'get_os_release_version_id', lambda x: '8.5')
    assert command_utils.get_target_version('default') == '9.0'


@mock.patch("leapp.cli.commands.command_utils.get_upgrade_paths_config",
            return_value={"default": {"7.9": ["8.4"], "8.6": ["9.0"], "7": ["8.4"], "8": ["9.0"]}})
def test_vet_upgrade_path(mock_open, monkeypatch):
    monkeypatch.setattr(command_utils, 'get_os_release_version_id', lambda x: '8.6')

    # make sure env var LEAPP_DEVEL_TARGET_RELEASE takes precedence
    # when env var set to a bad version - abort the upgrade
    args = mock.Mock(target='9.0')
    monkeypatch.setenv('LEAPP_DEVEL_TARGET_RELEASE', '1.2badsemver')
    with pytest.raises(CommandError) as err:
        command_utils.vet_upgrade_path(args)
        assert 'Unexpected format of target version' in err
    # MAJOR.MINOR.PATCH is considered as bad version, only MAJOR.MINOR is accepted
    args = mock.Mock(target='9.0')
    monkeypatch.setenv('LEAPP_DEVEL_TARGET_RELEASE', '9.0.0')
    with pytest.raises(CommandError) as err:
        command_utils.vet_upgrade_path(args)
        assert 'Unexpected format of target version' in err
    # when env var set to a version not in upgrade_paths map - go on and use it
    monkeypatch.setenv('LEAPP_DEVEL_TARGET_RELEASE', '1.2')
    assert command_utils.vet_upgrade_path(args) == ('1.2', 'default')
    # no env var set, --target is set to proper version
    monkeypatch.delenv('LEAPP_DEVEL_TARGET_RELEASE', raising=False)
    assert command_utils.vet_upgrade_path(args) == ('9.0', 'default')
    # env var is set to proper version, --target is set to a bad one - use env var and go on with the upgrade
    monkeypatch.setenv('LEAPP_DEVEL_TARGET_RELEASE', '9.0')
    args = mock.Mock(target='1.2')
    assert command_utils.vet_upgrade_path(args) == ('9.0', 'default')
