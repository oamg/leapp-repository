import os

import pytest

from leapp.models import SelinuxPermissiveDecision


@pytest.mark.skipif(
    os.getenv("DESTRUCTIVE_TESTING", False) in [False, "0"],
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
    os.getenv("DESTRUCTIVE_TESTING", False) in [False, "0"],
    reason='Test disabled by default because it would modify the system')
def test_set_selinux_permissive(current_actor_context):
    current_actor_context.feed(SelinuxPermissiveDecision(set_permissive=True))
    current_actor_context.run()
    assert check_permissive_in_conf()
