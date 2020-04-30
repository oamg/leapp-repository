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
    ["999", "mock3"],
    ["400", "permissive_abrt_t"]
]

SEMANAGE_COMMANDS = [
    ['fcontext', '-t', 'ganesha_var_run_t', "'/ganesha(/.*)?'"],
    ['fcontext', '-t', 'httpd_sys_content_t', "'/web(/.*)?'"],
    ['port', '-t', 'http_port_t', '-p', 'udp', '81']
]


def _run_cmd(cmd, logmsg="", split=True):
    try:
        return run(cmd, split=split).get("stdout", "")
    except CalledProcessError as e:
        if logmsg:
            api.current_logger().warning("%s: %s", logmsg, str(e.stderr))


def find_module_semodule(semodule_lfull, name, priority):
    return next((line for line in semodule_lfull if (name in line and priority in line)), None)


def find_semanage_rule(rules, rule):
    return next((r for r in rules if all(word in r for word in rule)), None)


@pytest.fixture(scope="function")
def destructive_selinux_teardown():
    # actor introduces changes to the system, therefore only teardown is needed
    yield

    for priority, module in TEST_MODULES:
        _run_cmd(["semodule", "-X", priority, "-r", module],
                 "Error removing module {} after testing".format(module))

    for command in SEMANAGE_COMMANDS[1:]:
        _run_cmd(["semanage", command[0], "-d"] + [x.strip('"\'') for x in command[1:]],
                 "Failed to remove SELinux customizations after testing")

    _run_cmd(["semanage", SEMANAGE_COMMANDS[0][0], "-d"] + SEMANAGE_COMMANDS[0][1:],
             "Failed to remove SELinux customizations after testing")


@pytest.mark.skipif(os.getenv("DESTRUCTIVE_TESTING", False) in [False, "0"],
                    reason='Test disabled by default because it would modify the system')
def test_SELinuxApplyCustom(current_actor_context, destructive_selinux_teardown):

    semodule_list = [SELinuxModule(name=module, priority=int(prio),
                                   content="(allow domain proc_type (file (getattr open read)))", removed=[])
                     for (prio, module) in TEST_MODULES]

    commands = [" ".join([c[0], "-a"] + c[1:]) for c in SEMANAGE_COMMANDS[1:]]
    semanage_removed = [" ".join([SEMANAGE_COMMANDS[0][0], "-a"] + SEMANAGE_COMMANDS[0][1:])]

    current_actor_context.feed(SELinuxModules(modules=semodule_list))
    current_actor_context.feed(SELinuxCustom(commands=commands, removed=semanage_removed))
    current_actor_context.run()

    semodule_lfull = _run_cmd(["semodule", "-lfull"],
                              "Error listing selinux modules")
    semanage_export = _run_cmd(["semanage", "export"],
                               "Error listing selinux customizations")

    # check that all reported modules where introduced to the system
    for priority, name in TEST_MODULES:
        if priority not in ('100', '200'):
            assert find_module_semodule(semodule_lfull, name, priority)
    # check that all valid commands where introduced to the system
    for command in SEMANAGE_COMMANDS[1:-1]:
        assert find_semanage_rule(semanage_export, command)
