import os

import pytest

from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import SELinuxCustom, SELinuxFacts, SELinuxModule, SELinuxModules, SELinuxRequestRPMs
from leapp.reporting import Report

TEST_MODULES = [
    ["400", "mock1"],
    ["99", "mock1"],
    ["200", "mock1"],
    ["400", "mock2"],
    ["999", "mock3"],
    ["400", "permissive_abrt_t"]
]

TEST_TEMPLATES = [
    ["200", "base_container"],
    ["200", "home_container"],
]

# [0] will be passed to the actor as "removed"
# [1] will not be passed to the actor and should not be removed
# rest are valid and should be applied by the actor
SEMANAGE_COMMANDS = [
    ['fcontext', '-t', 'cgdcbxd_var_run_t', "'/ganesha(/.*)?'"],
    ['user', 'yolo', '-R', 'user_r'],
    ['fcontext', '-t', 'httpd_sys_content_t', "'/web(/.*)?'"],
    ['port', '-t', 'http_port_t', '-p', 'udp', '81']
]


def _run_cmd(cmd, logmsg="", split=True):
    try:
        return run(cmd, split=split).get("stdout", "")
    except CalledProcessError as e:
        if logmsg:
            api.current_logger().warning("{}: {}".format(logmsg, e.stderr))
    return None


def find_module_semodule(semodule_lfull, name, priority):
    return next((line for line in semodule_lfull if (name in line and priority in line)), None)


def find_semanage_rule(rules, rule):
    return next((r for r in rules if all(word in r for word in rule)), None)


@pytest.fixture(scope="function")
def destructive_selinux_env():
    # apply SEMANAGE_COMMANDS[1] so that we can test that the actor did not remove it
    _run_cmd(["semanage", SEMANAGE_COMMANDS[1][0], "-a"] + SEMANAGE_COMMANDS[1][1:],
             "Error applying selinux customizations before test")

    yield

    semodule_command = ["semodule"]
    for priority, module in TEST_MODULES:
        semodule_command.extend(["-X", priority, "-r", module])
    _run_cmd(semodule_command, "Error removing modules after testing!")

    for command in SEMANAGE_COMMANDS:
        _run_cmd(["semanage", command[0], "-d"] + [x.strip('"\'') for x in command[1:]],
                 "Failed to remove SELinux customizations after testing")


@pytest.mark.skipif(os.getenv("DESTRUCTIVE_TESTING", False) in [False, "0"],
                    reason='Test disabled by default because it would modify the system')
def test_SELinuxApplyCustom(current_actor_context, destructive_selinux_teardown):

    semodule_list = [SELinuxModule(name=module, priority=int(prio),
                                   content="(allow domain proc_type (file (getattr open read)))", removed=[])
                     for (prio, module) in TEST_MODULES]
    template_list = [SELinuxModule(name=module, priority=int(prio),
                                   content="", removed=[])
                     for (prio, module) in TEST_TEMPLATES]

    commands = [" ".join([c[0], "-a"] + c[1:]) for c in SEMANAGE_COMMANDS[2:]]
    semanage_removed = [" ".join([SEMANAGE_COMMANDS[0][0], "-a"] + SEMANAGE_COMMANDS[0][1:])]

    current_actor_context.feed(SELinuxModules(modules=semodule_list, templates=template_list))
    current_actor_context.feed(SELinuxCustom(commands=commands, removed=semanage_removed))
    current_actor_context.run()

    semodule_lfull = _run_cmd(["semodule", "-lfull"],
                              "Error listing selinux modules")
    semanage_export = _run_cmd(["semanage", "export"],
                               "Error listing selinux customizations")

    # check that all reported modules where introduced to the system
    for priority, name in TEST_MODULES + TEST_TEMPLATES:
        if priority not in ('100', '200'):
            assert find_module_semodule(semodule_lfull, name, priority)
    # check that all valid commands where introduced to the system (SEMANAGE_COMMANDS[2:])
    # and that SEMANAGE_COMMANDS[1] was not removed
    for command in SEMANAGE_COMMANDS[1:-1]:
        assert find_semanage_rule(semanage_export, command)
