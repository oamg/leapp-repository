import os

import pytest

from leapp.libraries.actor import setpermissiveselinux
from leapp.libraries.stdlib import CalledProcessError
from leapp.models import SelinuxPermissiveDecision

_SED_ERROR = "/bin/sed: cannot rename /etc/selinux/sedXXXXXX: Operation not permitted"


@pytest.mark.skipif(
    os.getenv("DESTRUCTIVE_TESTING", "0").lower() in ["0", "false"],
    reason='Test disabled by default because it would modify the system')
def check_permissive_in_conf():
    """ Check if we have set permissive in SElinux conf file """
    with open('/etc/selinux/config') as fo:
        result = [l for l in (line.strip() for line in fo) if l]
        for res in result:
            if res == "SELINUX=permissive":
                return True
    return False


@pytest.mark.skipif(
    os.getenv("DESTRUCTIVE_TESTING", "false").lower() in ["0", "false"],
    reason='Test disabled by default because it would modify the system')
def test_set_selinux_permissive(current_actor_context):
    current_actor_context.feed(SelinuxPermissiveDecision(set_permissive=True))
    current_actor_context.run()
    assert check_permissive_in_conf()


def test_selinux_set_permissive_returns_stderr_on_failure(monkeypatch):
    def run_failing(cmd):
        raise CalledProcessError(
            message='A Leapp Command Error occurred.',
            command=cmd,
            result={'stdout': '', 'stderr': _SED_ERROR, 'exit_code': 4, 'signal': 0},
        )

    monkeypatch.setattr(setpermissiveselinux, 'run', run_failing)

    assert setpermissiveselinux.selinux_set_permissive() == (False, _SED_ERROR)


def test_selinux_set_permissive_success(monkeypatch):
    monkeypatch.setattr(setpermissiveselinux, 'run', lambda cmd: {'exit_code': 0})

    assert setpermissiveselinux.selinux_set_permissive() == (True, None)
