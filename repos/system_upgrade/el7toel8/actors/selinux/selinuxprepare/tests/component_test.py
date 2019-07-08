import os

import pytest

from leapp.snactor.fixture import current_actor_context
from leapp.models import SELinuxModule, SELinuxModules, SELinuxCustom
from leapp.libraries.stdlib import api, run, CalledProcessError
from leapp.reporting import Report


TEST_MODULES = [
    ["400", "mock1"],
    ["99", "mock1"],
    ["300", "mock1"],
    ["400", "mock2"],
    ["999", "mock3"]
]

SEMANAGE_COMMANDS = [
    ['fcontext', '-t', 'httpd_sys_content_t', '"/web(/.*)?"'],
    ['fcontext', '-t', 'ganesha_var_run_t', '"/ganesha(/.*)?"'],
    ['port', '-t', 'http_port_t', '-p', 'udp', '81'],
    ['permissive', 'abrt_t']
]

testmoduledir = "tests/mock_modules/"


def _run_cmd(cmd, split=False, logmsg=""):
    try:
        return run(cmd, split=split).get("stdout", "")
    except CalledProcessError as e:
        # XXX FIXME not sure logging in tests makes sense
        api.current_logger().warning("%s: %s", logmsg, str(e.stderr))


SEMODULE_LFULL_INITIAL = _run_cmd(["semodule", "-lfull"], logmsg="Error listing SELinux customizations")
SEMANAGE_EXPORT_INITIAL = _run_cmd(["semanage", "export"], logmsg="Error listing SELinux customizations")


def setup():
    # NOTE(ivasilev) Maybe there is a more elegant way to conditionally run setup/teardown
    enabled = os.environ.get("DESTRUCTIVE_TESTING", False)
    if not enabled:
        return

    for priority, module in TEST_MODULES:
        tests_dir = os.path.join(os.getenv('PYTEST_CURRENT_TEST').rsplit(os.path.sep, 2)[0], testmoduledir)
        _run_cmd(["semodule", "-X", priority, "-i", os.path.join(tests_dir, module + ".cil")],
                 logmsg="Error installing mock module")

    for command in SEMANAGE_COMMANDS:
        _run_cmd(["semanage", command[0], "-a"] + command[1:], logmsg="Error applying selinux customizations")


@pytest.mark.skipif(not os.environ.get("DESTRUCTIVE_TESTING", False),
                    reason='Test disabled by default because it would modify the system')
def test_SELinuxPrepare(current_actor_context):
    for cmd in (["semodule", "-lfull"], ["semanage", "export"]):
        res = _run_cmd(cmd)
        api.current_logger().info("Before test:%s", res)

    # XXX FIXME test_modules.reverse() returns None and changes underlying list which should not happen
    # to global vars. Removing that reversing as it is broken anyway
    semodule_list = [SELinuxModule(name=module, priority=int(prio), content="", removed=[])
                     for (prio, module) in TEST_MODULES + [["400", "permissive_abrt_t"]]]

    current_actor_context.feed(SELinuxModules(modules=semodule_list))
    current_actor_context.run()

    # check if all given modules and local customizations where removed
    semodule_res = _run_cmd(["semodule", "-lfull"])
    assert SEMODULE_LFULL_INITIAL == semodule_res
    semanage_res = _run_cmd(["semanage", "export"])
    assert SEMANAGE_EXPORT_INITIAL == semanage_res


def teardown():
    # NOTE(ivasilev) Maybe there is a more elegant way to conditionally run setup/teardown
    enabled = os.environ.get("DESTRUCTIVE_TESTING", False)
    if not enabled:
        return

    for priority, module in TEST_MODULES + [["400", "permissive_abrt_t"]]:
        # failure is expected -- should be removed by the actor
        # XXX FIXME if failure is 100% expected - use assertRaises
        _run_cmd(["semodule", "-X", priority, "-r", module])

    for command in SEMANAGE_COMMANDS:
        # failure is expected -- should be removed by the actor
        # XXX FIXME if failure is 100% expected - use assertRaises
        _run_cmd(["semanage", command[0], "-d"] + command[1:])
