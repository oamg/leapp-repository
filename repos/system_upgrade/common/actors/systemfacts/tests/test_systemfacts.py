import grp
import pwd

import pytest

from leapp.libraries.actor.systemfacts import _get_system_groups, _get_system_users, anyendswith, anyhasprefix, aslist
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api
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

    class MockedPwdEntry(object):
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

    class MockedGrpEntry(object):
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
