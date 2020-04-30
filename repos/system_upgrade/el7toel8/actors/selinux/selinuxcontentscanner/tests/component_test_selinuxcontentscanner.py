import os

import pytest

from leapp.snactor.fixture import current_actor_context
from leapp.models import SELinuxModule, SELinuxModules, SELinuxCustom, SELinuxFacts, SELinuxRequestRPMs
from leapp.libraries.stdlib import api, run, CalledProcessError
from leapp.reporting import Report

TEST_MODULES = [
    ["400", "mock1"],
    ["99", "mock1"],
    ["200", "mock1"],
    ["400", "mock2"],
    ["999", "mock3"]
]

SEMANAGE_COMMANDS = [
    ['fcontext', '-t', 'httpd_sys_content_t', '"/web(/.*)?"'],
    ['fcontext', '-t', 'cgdcbxd_unit_file_t', '"cgdcbxd/(/.*)?"'],
    ['port', '-t', 'http_port_t', '-p', 'udp', '81'],
    ['permissive', 'abrt_t']
]

testmoduledir = "tests/mock_modules/"


def _run_cmd(cmd, logmsg="", split=False):
    try:
        return run(cmd, split=split).get("stdout", "")
    except CalledProcessError as e:
        # Only report issues when they are explicitly described.
        # This way expected failures are not reported.
        if logmsg:
            api.current_logger().warning("%s: %s", logmsg, str(e.stderr))


@pytest.fixture(scope="function")
def destructive_selinux_env():
    tests_dir = os.path.join(os.path.realpath(__file__).rsplit(os.path.sep, 2)[0], testmoduledir)
    for priority, module in TEST_MODULES:
        _run_cmd(["semodule", "-X", priority, "-i", os.path.join(tests_dir, module + ".cil")],
                 "Error installing mock module {} before test".format(module))

    for command in SEMANAGE_COMMANDS:
        _run_cmd(["semanage", command[0], "-a"] + command[1:],
                 "Error applying selinux customizations before test")

    yield

    for command in SEMANAGE_COMMANDS[:-1]:
        _run_cmd(["semanage", command[0], "-d"] + command[1:],
                 "Error removing selinux customizations after testing")

    for priority, module in reversed(TEST_MODULES + [["400", "permissive_abrt_t"]]):
        _run_cmd(["semodule", "-X", priority, "-r", module],
                 "Error removing selinux module {} after testing".format(module))


def find_module(selinuxmodules, name, priority):
    return next((module for module in selinuxmodules.modules
                if (module.name == name and module.priority == int(priority))), None)


def find_semanage_rule(rules, rule):
    return next((r for r in rules if all(word in r for word in rule)), None)


@pytest.mark.skipif(os.getenv("DESTRUCTIVE_TESTING", False) in [False, "0"],
                    reason='Test disabled by default because it would modify the system')
def test_SELinuxContentScanner(current_actor_context, destructive_selinux_env):

    expected_data = {'policy': 'targeted',
                     'mls_enabled': True,
                     'enabled': True,
                     'runtime_mode': 'enforcing',
                     'static_mode': 'enforcing'}

    current_actor_context.feed(SELinuxFacts(**expected_data))
    current_actor_context.run()

    modules = current_actor_context.consume(SELinuxModules)[0]
    api.current_logger().warning("Modules: %s", str(modules))
    assert modules
    # check that all modules installed during test setup where reported
    for priority, name in TEST_MODULES:
        if priority not in ('100', '200'):
            assert find_module(modules, name, priority)

    rpms = current_actor_context.consume(SELinuxRequestRPMs)[0]
    assert rpms
    # modules with priority 200 should only originate in "<module_name>-selinux" rpms
    assert "mock1-selinux" in rpms.to_keep
    # mock1 contains container related type
    assert "container-selinux" in rpms.to_install

    custom = current_actor_context.consume(SELinuxCustom)[0]
    assert custom
    # the second command contains removed type and should be discarded
    assert find_semanage_rule(custom.removed, SEMANAGE_COMMANDS[1])
    # the rest of the commands should be reported (except for the last which will show up in modules)
    assert find_semanage_rule(custom.commands, SEMANAGE_COMMANDS[0])
    assert find_semanage_rule(custom.commands, SEMANAGE_COMMANDS[2])
