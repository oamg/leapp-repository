import os

from leapp.snactor.fixture import current_actor_context
from leapp.models import SELinuxModule, SELinuxModules, SELinuxCustom, SELinuxFacts, SELinuxRequestRPMs
from leapp.libraries.stdlib import api, run, CalledProcessError
from leapp.reporting import Report

test_modules = [
    ["400", "mock1"],
    ["99", "mock1"],
    ["200", "mock1"],
    ["400", "mock2"],
    ["999", "mock3"],
    ["400", "permissive_abrt_t"]
]

semanage_commands = [
['fcontext', '-t', 'ganesha_var_run_t', "'/ganesha(/.*)?'"],
['fcontext', '-t', 'httpd_sys_content_t', "'/web(/.*)?'"],
['port', '-t', 'http_port_t', '-p', 'udp', '81']
]

def findModuleSemodule(semodule_lfull, name, priority):
    for line in semodule_lfull:
        if name in line and priority in line:
            return line
    return None

def findSemanageRule(rules, rule):
    for r in rules:
        for word in rule:
            if word not in r:
                break
        else:
            return r
    return None

def test_SELinuxApplyCustom(current_actor_context):

    semodule_list = [SELinuxModule(name=module, priority=int(prio),
                                   content="(allow domain proc_type (file (getattr open read)))", removed=[])
                                   for (prio, module) in test_modules]

    commands = [" ".join([c[0], "-a"] + c[1:]) for c in semanage_commands[1:]]
    semanage_removed = [" ".join([semanage_commands[0][0], "-a"] + semanage_commands[0][1:])]

    current_actor_context.feed(SELinuxModules(modules=semodule_list))
    current_actor_context.feed(SELinuxCustom(commands=commands, removed=semanage_removed))
    current_actor_context.run()

    # check if all given modules and local customizations where removed
    semodule_lfull = []
    semanage_export = []
    try:
        semodule = run(["semodule", "-lfull"], split=True)
        semodule_lfull = semodule.get("stdout", "")
        semanage = run(["semanage", "export"], split=True)
        semanage_export = semanage.get("stdout", "")
    except CalledProcessError as e:
        api.current_logger().warning("Error listing selinux customizations: %s", str(e.stderr))
        assert False

    # check that all modules installed during test setup where reported
    for priority, name in test_modules:
        if priority != "100" and priority != "200":
            assert findModuleSemodule(semodule_lfull, name, priority)
    # check that all valid commands where reintroduced to the system
    for command in semanage_commands[1:-1]:
        assert findSemanageRule(semanage_export, command)

def teardown():
    for priority, module in test_modules:
        try:
            run(["semodule", "-X", priority, "-r", module])
        except CalledProcessError as e:
            # expected if the test fails
            api.current_logger().warning("Error removing selinux modules after testing: %s", str(e.stderr))

    for command in semanage_commands[1:]:
        try:
            run(["semanage", command[0], "-d"] + [x.strip('"\'') for x in command[1:]])
        except CalledProcessError as e:
            # expected if the test fails
            api.current_logger().warning("Error removing selinux customizations after testing: %s", str(e.stderr))
            continue

    try:
        run(["semanage", semanage_commands[0][0], "-d"] + semanage_commands[0][1:])
    except CalledProcessError:
        # expected
        pass
