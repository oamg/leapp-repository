import os

import pytest

from leapp.libraries.stdlib import api, run, CalledProcessError
from leapp.models import SELinuxModule, SELinuxModules, SELinuxCustom
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context


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


def _run_cmd(cmd, logmsg="", split=False):
    try:
        return run(cmd, split=split).get("stdout", "")
    except CalledProcessError as e:
        if logmsg:
            api.current_logger().warning("%s: %s", logmsg, str(e.stderr))


@pytest.fixture(scope="module")
def semodule_lfull_initial():
    yield _run_cmd(["semodule", "-lfull"], logmsg="Error listing SELinux customizations")


@pytest.fixture(scope="module")
def semanage_export_initial():
    yield _run_cmd(["semanage", "export"], logmsg="Error listing SELinux customizations")


@pytest.fixture(scope="function")
def destructive_selinux_env():
    for priority, module in TEST_MODULES:
        tests_dir = os.path.join(os.getenv('PYTEST_CURRENT_TEST').rsplit(os.path.sep, 2)[0], testmoduledir)
        _run_cmd(["semodule", "-X", priority, "-i", os.path.join(tests_dir, module + ".cil")],
                 logmsg="Error installing mock module")

    for command in SEMANAGE_COMMANDS:
        _run_cmd(["semanage", command[0], "-a"] + command[1:], logmsg="Error applying selinux customizations")

    yield

    for priority, module in TEST_MODULES + [["400", "permissive_abrt_t"]]:
        _run_cmd(["semodule", "-X", priority, "-r", module])

    for command in SEMANAGE_COMMANDS:
        _run_cmd(["semanage", command[0], "-d"] + command[1:])


@pytest.mark.skipif(os.getenv("DESTRUCTIVE_TESTING", False) in [False, "0"],
                    reason='Test disabled by default because it would modify the system')
def test_SELinuxPrepare(current_actor_context, semodule_lfull_initial, semanage_export_initial,
                        destructive_selinux_env):
    before_test = []
    for cmd in (["semodule", "-lfull"], ["semanage", "export"]):
        res = _run_cmd(cmd, "Error listing SELinux customizations")
        before_test.append(res)
        # XXX still not sure about logging in tests
        api.current_logger().info("Before test:%s", res)
    # Make sure that initial semodule/semanage commands don't match before tests ones
    assert before_test != [semodule_lfull_initial, semanage_export_initial]

    # XXX FIXME test_modules.reverse() returns None and changes underlying list which should not happen
    # to global vars. Removing that reversing as it is broken anyway
    semodule_list = [SELinuxModule(name=module, priority=int(prio), content="", removed=[])
                     for (prio, module) in TEST_MODULES + [["400", "permissive_abrt_t"]]]

    current_actor_context.feed(SELinuxModules(modules=semodule_list))
    current_actor_context.run()

    # check if all given modules and local customizations where removed
    semodule_res = _run_cmd(["semodule", "-lfull"], "Error listing SELinux modules")
    assert semodule_lfull_initial == semodule_res
    semanage_res = _run_cmd(["semanage", "export"], "Error listing SELinux customizations")
    assert semanage_export_initial == semanage_res
