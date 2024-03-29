import os

import pytest

from leapp.libraries.common.config import mock_configs
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import SELinuxCustom, SELinuxFacts, SELinuxModule, SELinuxModules, SELinuxRequestRPMs
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context

# compat module ensures compatibility with newer systems and is not part of testing
TEST_MODULES = [
    ["400", "mock1"],
    ["99", "mock1"],
    ["200", "mock1"],
    ["400", "mock2"],
    ["999", "mock3"],
    ["100", "compat"],
    ["200", "base_container"]
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
            api.current_logger().warning("{}: {}".format(logmsg, e.stderr))
    return None


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


def find_template(selinuxmodules, name, priority):
    return next((module for module in selinuxmodules.templates
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
    current_actor_context.run(config_model=mock_configs.CONFIG)

    modules = current_actor_context.consume(SELinuxModules)[0]
    assert modules
    # check that all modules installed during test setup where reported
    for priority, name in TEST_MODULES:
        if priority not in ('100', '200'):
            assert find_module(modules, name, priority)
    # check that udica template was reported
    assert find_template(modules, TEST_MODULES[-1][1], TEST_MODULES[-1][0])

    rpms = current_actor_context.consume(SELinuxRequestRPMs)[0]
    assert rpms

    # mock1 contains container related type
    assert "container-selinux" in rpms.to_install

    custom = current_actor_context.consume(SELinuxCustom)[0]
    assert custom
    # The second command contains removed type and should be discarded (in either upgrade path)
    assert find_semanage_rule(custom.removed, SEMANAGE_COMMANDS[1])
    # the rest of the commands should be reported (except for the last which will show up in modules)
    assert find_semanage_rule(custom.commands, SEMANAGE_COMMANDS[0])
    assert find_semanage_rule(custom.commands, SEMANAGE_COMMANDS[2])
