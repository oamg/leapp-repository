import os

import pytest

from leapp.snactor.fixture import current_actor_context
from leapp.models import SELinuxModule, SELinuxModules, SELinuxCustom, SELinuxFacts, SELinuxRequestRPMs
from leapp.libraries.stdlib import api, run, CalledProcessError
from leapp.reporting import Report

test_modules = [
    ["400", "mock1"],
    ["99", "mock1"],
    ["200", "mock1"],
    ["400", "mock2"],
    ["999", "mock3"]
]

semanage_commands = [
    ['fcontext', '-t', 'httpd_sys_content_t', '"/web(/.*)?"'],
    ['fcontext', '-t', 'ganesha_var_run_t', '"/ganesha(/.*)?"'],
    ['port', '-t', 'http_port_t', '-p', 'udp', '81'],
    ['permissive', 'abrt_t']
]

testmoduledir = os.path.join(os.getcwd(), "tests/mock_modules/")


# Test disabled because it's setup and teardown would modify the system
# Remove "_" before re-activation
def setup_():
    for priority, module in test_modules:
        try:
            semodule = run(["semodule", "-X", priority, "-i", os.path.join(testmoduledir, module + ".cil")])
        except CalledProcessError as e:
            api.current_logger().warning("Error installing mock module: %s", e.stderr)
            api.current_logger().warning("Error installing mock module: %s, %s", str(e.stderr),
                                         semodule.get("stderr", "fuck"))
            continue

    for command in semanage_commands:
        try:
            run(["semanage", command[0], "-a"] + command[1:])
        except CalledProcessError as e:
            api.current_logger().warning("Error applying selinux customizations %s", str(e.stderr))
            continue


def findModule(selinuxmodules, name, priority):
    for module in selinuxmodules.modules:
        if module.name == name and module.priority == int(priority):
            return module
    return None


def findSemanageRule(rules, rule):
    for r in rules:
        for word in rule:
            if word not in r:
                break
        else:
            return r
    return None


@pytest.mark.skip(reason="Test disabled because it's setup and teardown would modify the system")
def test_SELinuxContentScanner(current_actor_context):

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
    for priority, name in test_modules:
        if priority != "100" and priority != "200":
            assert findModule(modules, name, priority)

    rpms = current_actor_context.consume(SELinuxRequestRPMs)[0]
    assert rpms
    # modules with priority 200 should only originate in "<module_name>-selinux" rpms
    assert "mock1-selinux" in rpms.to_keep
    # mock1 contains container related type
    assert "container-selinux" in rpms.to_install

    custom = current_actor_context.consume(SELinuxCustom)[0]
    assert custom
    # the second command contains removed type and should be discarded
    assert findSemanageRule(custom.removed, semanage_commands[1])
    # the rest of the commands should be reported (except for the last which will show up in modules)
    assert findSemanageRule(custom.commands, semanage_commands[0])
    assert findSemanageRule(custom.commands, semanage_commands[2])


# Test disabled because it's setup and teardown would modify the system
# Remove "_" before re-activation
def teardown_():
    for command in semanage_commands[:-1]:
        try:
            run(["semanage", command[0], "-d"] + command[1:])
        except CalledProcessError as e:
            api.current_logger().warning("Error removing selinux customizations after testing: %s", str(e.stderr))
            continue

    for priority, module in reversed(test_modules + [["400", "permissive_abrt_t"]]):
        try:
            run(["semodule", "-X", priority, "-r", module])
        except CalledProcessError as e:
            api.current_logger().warning("Error removing selinux modules after testing: %s", str(e.stderr))
            continue
