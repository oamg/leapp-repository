import grp
import os
import pwd
from unittest import mock

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import systemfacts
from leapp.libraries.actor.systemfacts import (
    _get_secure_boot_state,
    _get_system_groups,
    _get_system_users,
    anyendswith,
    anyhasprefix,
    aslist,
    get_firmware,
    get_repositories_status
)
from leapp.libraries.common import repofileutils
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import FirmwareFacts
from leapp.snactor.fixture import current_actor_libraries


def test_anyendswith(current_actor_libraries):
    value = 'this_is_a_test'

    assert anyendswith(value, ['a_test'])
    assert anyendswith(value, ['a_test', 'bgerwh', 'g52h4q'])
    assert anyendswith(value, ['est'])
    assert not anyendswith(value, ['asafsaf', 'gbfdshh', '123f', 'gdsgsnb'])
    assert not anyendswith(value, [])


def test_anyhasprefix(current_actor_libraries):
    value = 'this_is_a_test'

    assert anyhasprefix(value, ['this'])
    assert anyhasprefix(value, ['this', 'ddsvssd', 'bsdhn', '125fff'])
    assert anyhasprefix(value, ['this_is'])
    assert not anyhasprefix(value, ['ccbbb', 'xasbnn', 'xavavav', 'bbnkk1'])
    assert not anyhasprefix(value, [])


def test_aslist(current_actor_libraries):

    @aslist
    def local():
        yield True
        yield False
        yield True

    r = local()

    assert isinstance(r, list) and r[0] and r[2] and not r[1]


@pytest.mark.parametrize(
    ('etc_passwd_names', 'etc_passwd_directory', 'skipped_user_names'),
    [
        (['root', 'unbound', 'dbus'], '/', []),
        (['root', '+@scanners', 'dbus', '-@usrc', ''], '/', ['+@scanners', '-@usrc', '']),
        (['root', '+@scanners', 'dbus'], '', ['root', '+@scanners', 'dbus']),
    ]
)
def test_get_system_users(monkeypatch, etc_passwd_names, etc_passwd_directory, skipped_user_names):

    class MockedPwdEntry:
        def __init__(self, pw_name, pw_uid, pw_gid, pw_dir):
            self.pw_name = pw_name
            self.pw_uid = pw_uid
            self.pw_gid = pw_gid
            self.pw_dir = pw_dir

    etc_passwd_contents = []
    for etc_passwd_name in etc_passwd_names:
        etc_passwd_contents.append(MockedPwdEntry(etc_passwd_name, 0, 0, etc_passwd_directory))

    monkeypatch.setattr(pwd, 'getpwall', lambda: etc_passwd_contents)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    _get_system_users()

    if skipped_user_names:
        assert len(api.current_logger().dbgmsg) == 1

        for skipped_user_name in skipped_user_names:
            assert skipped_user_name in api.current_logger().dbgmsg[0]

        for user_name in etc_passwd_names:
            if user_name not in skipped_user_names:
                assert user_name not in api.current_logger().dbgmsg[0]
    else:
        assert not api.current_logger().dbgmsg


@pytest.mark.parametrize(
    ('etc_group_names', 'skipped_group_names'),
    [
        (['cdrom', 'floppy', 'tape'], []),
        (['cdrom', '+@scanners', 'floppy', '-@usrc', ''], ['+@scanners', '-@usrc', '']),
    ]
)
def test_get_system_groups(monkeypatch, etc_group_names, skipped_group_names):

    class MockedGrpEntry:
        def __init__(self, gr_name, gr_gid, gr_mem):
            self.gr_name = gr_name
            self.gr_gid = gr_gid
            self.gr_mem = gr_mem

    etc_group_contents = []
    for etc_group_name in etc_group_names:
        etc_group_contents.append(MockedGrpEntry(etc_group_name, 0, []))

    monkeypatch.setattr(grp, 'getgrall', lambda: etc_group_contents)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    _get_system_groups()

    if skipped_group_names:
        assert len(api.current_logger().dbgmsg) == 1

        for skipped_group_name in skipped_group_names:
            assert skipped_group_name in api.current_logger().dbgmsg[0]

        for group_name in etc_group_names:
            if group_name not in skipped_group_names:
                assert group_name not in api.current_logger().dbgmsg[0]
    else:
        assert not api.current_logger().dbgmsg


def test_failed_parsed_repofiles(monkeypatch):
    def _raise_invalidrepo_error():
        raise repofileutils.InvalidRepoDefinition(msg='mocked error',
                                                  repofile='/etc/yum.repos.d/mock.repo',
                                                  repoid='mocked repoid')

    monkeypatch.setattr(repofileutils, 'get_parsed_repofiles', _raise_invalidrepo_error)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    with pytest.raises(StopActorExecutionError):
        get_repositories_status()


@pytest.mark.parametrize('is_enabled', (True, False))
@mock.patch('leapp.libraries.actor.systemfacts.run')
def test_get_secure_boot_state_ok(mocked_run: mock.MagicMock, is_enabled):
    mocked_run.return_value = {
        'stdout': f'SecureBoot {"enabled" if is_enabled else "disabled"}'
    }

    out = _get_secure_boot_state()

    assert out == is_enabled
    mocked_run.assert_called_once_with(['mokutil', '--sb-state'])


@mock.patch('leapp.libraries.actor.systemfacts.run')
def test_get_secure_boot_state_no_mokutil(mocked_run: mock.MagicMock):
    mocked_run.side_effect = OSError

    out = _get_secure_boot_state()

    assert out is False
    mocked_run.assert_called_once_with(['mokutil', '--sb-state'])


@mock.patch('leapp.libraries.actor.systemfacts.run')
def test_get_secure_boot_state_not_supported(mocked_run: mock.MagicMock):
    cmd = ['mokutil', '--sb-state']
    result = {
        'stderr': "This system doesn't support Secure Boot",
        'exit_code': 255,
    }
    mocked_run.side_effect = CalledProcessError(
        "Command mokutil --sb-state failed with exit code 255.",
        cmd,
        result
    )

    out = _get_secure_boot_state()

    assert out is None
    mocked_run.assert_called_once_with(cmd)


@mock.patch('leapp.libraries.actor.systemfacts.run')
def test_get_secure_boot_state_failed(mocked_run: mock.MagicMock):
    cmd = ['mokutil', '--sb-state']
    result = {
        'stderr': 'EFI variables are not supported on this system',
        'exit_code': 1,
    }
    mocked_run.side_effect = CalledProcessError(
        "Command mokutil --sb-state failed with exit code 1.",
        cmd,
        result
    )

    with pytest.raises(
        StopActorExecutionError,
        match='Failed to determine SecureBoot state'
    ):
        _get_secure_boot_state()

    mocked_run.assert_called_once_with(cmd)


def _ff(firmware, ppc64le_opal, is_secureboot):
    return FirmwareFacts(
        firmware=firmware,
        ppc64le_opal=ppc64le_opal,
        secureboot_enabled=is_secureboot
    )


@pytest.mark.parametrize(
    "has_sys_efi, has_sys_opal, is_ppc, secboot_state, expect",
    [
        # 1. Standard BIOS on x86
        (False, False, False, None, _ff("bios", None, None)),
        # 2. EFI on x86 with Secure Boot Enabled
        (True,  False, False, True,  _ff("efi",  None, True)),
        # 3. EFI on x86 with Secure Boot Disabled
        (True,  False, False, False, _ff("efi",  None, False)),
        # 4. PPC64LE with OPAL (No EFI)
        (False, True,  True,  None,  _ff("bios", True, None)),
        # 5. PPC64LE without OPAL (No EFI)
        (False, False, True,  None,  _ff("bios", False, None)),
        # 6. EFI on PPC64LE with OPAL
        (True,  True,  True,  True,  _ff("efi",  True, True)),
    ]
)
def test_get_firmware_logic(
    has_sys_efi, has_sys_opal, is_ppc, secboot_state, expect
):
    with mock.patch('os.path.isdir') as mock_isdir, \
         mock.patch('leapp.libraries.stdlib.api.current_actor') as mock_curr_actor, \
         mock.patch('leapp.libraries.actor.systemfacts._get_secure_boot_state') as mock_get_sb_state:

        mock_isdir.side_effect = lambda path: {
            '/sys/firmware/efi': has_sys_efi,
            '/sys/firmware/opal/': has_sys_opal
        }.get(path, False)

        mock_curr_actor.return_value = CurrentActorMocked(
            arch=architecture.ARCH_PPC64LE if is_ppc else architecture.ARCH_X86_64
        )
        mock_get_sb_state.return_value = secboot_state

        result = get_firmware()

        assert result == expect
