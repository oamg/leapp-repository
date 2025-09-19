import os
import resource

import mock
import pytest

from leapp.cli.commands import command_utils
from leapp.exceptions import CommandError


@mock.patch(
    "leapp.cli.commands.command_utils.get_upgrade_paths_config",
    return_value={
        "rhel": {
            "default": {"7.9": ["8.4"], "8.6": ["9.0"], "8.7": ["9.1"], "7": ["8.4"], "8": ["9.0"]}
        },
        "centos": {
            "default": {"8": ["9"], "9": ["10"]},
            "_virtual_versions": {"8": "8.7", "9": "9.8", "10": "10.2"},
        },
        "alma": {
            "default": {"7.9": ["8.4"], "8.6": ["9.0"], "8.7": ["9.1"]}
        },
    },
)
def test_get_target_version(mock_open, monkeypatch):

    def set_etc_osrelease(distro_id, version_id):
        etc_os_release_contents = {"ID": distro_id, "VERSION_ID": version_id}
        monkeypatch.setattr(
            command_utils,
            "_retrieve_os_release_contents",
            lambda *args, **kwargs: etc_os_release_contents,
        )

    set_etc_osrelease('rhel', '8.6')
    assert command_utils.get_target_version('default', 'rhel') == '9.0'

    # the envar should not affect this function
    monkeypatch.setenv('LEAPP_DEVEL_TARGET_RELEASE', '')
    assert command_utils.get_target_version('default', 'rhel') == '9.0'

    # unsupported path, matches because of the major version fallback
    monkeypatch.delenv('LEAPP_DEVEL_TARGET_RELEASE', raising=True)
    set_etc_osrelease('rhel', '8.5')
    assert command_utils.get_target_version('default', 'rhel') == '9.0'

    # centos->centos
    set_etc_osrelease('centos', '9')
    assert command_utils.get_target_version('default', 'centos') == '10'

    # centos->rhel, lookup based on virtual versions
    set_etc_osrelease('centos', '8')
    assert command_utils.get_target_version('default', 'rhel') == '9.1'

    # rhel->centos, reverse virtual versions lookup
    set_etc_osrelease('rhel', '8.6')
    assert command_utils.get_target_version('default', 'centos') == '9'


@mock.patch(
    "leapp.cli.commands.command_utils.get_upgrade_paths_config",
    return_value={
        "default": {
            "7.9": ["8.4"],
            "8.6": ["9.0", "9.2"],
            "7": ["8.4"],
            "8": ["9.0", "9.2"],
        }
    },
)
def test_get_target_release(mock_open, monkeypatch):  # do not remove mock_open
    # NOTE Not testing with other distros, the tested function is mainly about
    # handling of the CLI option, envar and format checking, the real target
    # release retrieval is handled in get_target_version which is tested with
    # different source/target distro combinanations elsewhere.

    # Make it look like it's RHEL even on centos, because that's what the test
    # assumes.
    # Otherwise the test, when ran on Centos, fails because it works
    # with MAJOR.MINOR version format while Centos uses MAJOR format.
    monkeypatch.setattr(command_utils, 'get_source_distro_id', lambda: 'rhel')
    monkeypatch.setattr(command_utils, 'get_os_release_version_id', lambda x: '8.6')

    # make sure env var LEAPP_DEVEL_TARGET_RELEASE takes precedence
    args = mock.Mock(target_version='9.0')
    monkeypatch.setenv('LEAPP_DEVEL_TARGET_RELEASE', '9.2')
    print(os.getenv('LEAPP_DEVEL_TARGET_RELEASE'))
    assert command_utils.get_target_release(args) == ('9.2', 'default')

    # when env var set to a bad version, expect an error
    monkeypatch.setenv('LEAPP_DEVEL_TARGET_RELEASE', '9.0.0')
    with pytest.raises(CommandError) as err:
        command_utils.get_target_release(args)
        assert 'Unexpected format of target version' in err

    # when env var set to a version not in upgrade_paths map - go on and use it
    # this is checked by an actor in the IPU
    monkeypatch.setenv('LEAPP_DEVEL_TARGET_RELEASE', '1.2')
    assert command_utils.get_target_release(args) == ('1.2', 'default')

    # no env var set, --target is set to proper version - use it
    args = mock.Mock(target_version='9.0')
    monkeypatch.delenv('LEAPP_DEVEL_TARGET_RELEASE', raising=False)
    assert command_utils.get_target_release(args) == ('9.0', 'default')

    # --target set with incorrectly formatted version, env var not set, fail
    args = mock.Mock(target_version='9.0a')
    with pytest.raises(CommandError) as err:
        command_utils.get_target_release(args)
        assert 'Unexpected format of target version' in err

    # env var is set to proper version, --target set to a bad one:
    # env var has priority, use it and go on with the upgrade
    monkeypatch.setenv('LEAPP_DEVEL_TARGET_RELEASE', '9.0')
    args = mock.Mock(target_version='9.0.0')
    assert command_utils.get_target_release(args) == ('9.0', 'default')


def _mock_getrlimit_factory(nofile_limits=(1024, 4096), fsize_limits=(1024, 4096)):
    """
    Factory function to create a mock `getrlimit` function with configurable return values.
    The default param values are lower than the expected values.

    :param nofile_limits: Tuple representing (soft, hard) limits for `RLIMIT_NOFILE`
    :param fsize_limits: Tuple representing (soft, hard) limits for `RLIMIT_FSIZE`
    :return: A mock `getrlimit` function
    """
    def mock_getrlimit(resource_type):
        if resource_type == resource.RLIMIT_NOFILE:
            return nofile_limits
        if resource_type == resource.RLIMIT_FSIZE:
            return fsize_limits
        return (0, 0)

    return mock_getrlimit


@pytest.mark.parametrize("nofile_limits, fsize_limits, expected_calls", [
    # Case where both limits need to be increased
    ((1024, 4096), (1024, 4096), [
        (resource.RLIMIT_NOFILE, (1024*16, 1024*16)),
        (resource.RLIMIT_FSIZE, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
    ]),
    # Case where neither limit needs to be changed
    ((1024*16, 1024*16), (resource.RLIM_INFINITY, resource.RLIM_INFINITY), [])
])
def test_set_resource_limits_increase(monkeypatch, nofile_limits, fsize_limits, expected_calls):
    setrlimit_called = []

    def mock_setrlimit(resource_type, limits):
        setrlimit_called.append((resource_type, limits))

    monkeypatch.setattr(resource, "getrlimit", _mock_getrlimit_factory(nofile_limits, fsize_limits))
    monkeypatch.setattr(resource, "setrlimit", mock_setrlimit)

    command_utils.set_resource_limits()

    assert setrlimit_called == expected_calls


@pytest.mark.parametrize("errortype, expected_message", [
    (OSError, "Failed to set resource limit"),
    (ValueError, "Failure occurred while attempting to set soft limit higher than the hard limit")
])
def test_set_resource_limits_exceptions(monkeypatch, errortype, expected_message):
    monkeypatch.setattr(resource, "getrlimit", _mock_getrlimit_factory())

    def mock_setrlimit(*args, **kwargs):
        raise errortype("mocked error")

    monkeypatch.setattr(resource, "setrlimit", mock_setrlimit)

    with pytest.raises(CommandError, match=expected_message):
        command_utils.set_resource_limits()
