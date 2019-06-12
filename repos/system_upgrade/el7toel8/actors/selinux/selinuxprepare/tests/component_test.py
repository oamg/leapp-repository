import os

import pytest

from leapp.snactor.fixture import current_actor_context
from leapp.models import SELinuxModule, SELinuxModules, SELinuxCustom
from leapp.libraries.stdlib import api, run, CalledProcessError
from leapp.reporting import Report

enabled = False

test_modules = [
    ["400", "mock1"],
    ["99", "mock1"],
    ["300", "mock1"],
    ["400", "mock2"],
    ["999", "mock3"]
]

semanage_commands = [
    ['fcontext', '-t', 'httpd_sys_content_t', '"/web(/.*)?"'],
    ['fcontext', '-t', 'ganesha_var_run_t', '"/ganesha(/.*)?"'],
    ['port', '-t', 'http_port_t', '-p', 'udp', '81'],
    ['permissive', 'abrt_t']
]

# save value of semodule -lfull for comparison
semodule_lfull = ""
semanage_export = ""

if enabled:
    try:
        semodule = run(["semodule", "-lfull"], split=False)
        semodule_lfull = semodule.get("stdout", "")
        semanage = run(["semanage", "export"], split=False)
        semanage_export = semanage.get("stdout", "")
    except CalledProcessError as e:
        api.current_logger().warning("Error listing SELinux customizations: %s", str(e.stderr))

testmoduledir = os.path.join(os.getcwd(), "tests/mock_modules/")


def setup():
    if enabled:
        for priority, module in test_modules:
            try:
                run(["semodule", "-X", priority, "-i", os.path.join(testmoduledir, module + ".cil")])
            except CalledProcessError as e:
                api.current_logger().warning("Error installing mock module: %s", str(e.stderr))
                continue

        for command in semanage_commands:
            try:
                run(["semanage", command[0], "-a"] + command[1:])
            except CalledProcessError as e:
                api.current_logger().warning("Error applying selinux customizations %s", str(e.stderr))
                continue


@pytest.mark.skip(reason='Test disabled because it would modify the system')
def test_SELinuxPrepare(current_actor_context):
    try:
        semodule = run(["semodule", "-lfull"], split=False)
        api.current_logger().info("Before test:" + semodule.get("stdout", ""))
        semanage = run(["semanage", "export"], split=False)
        api.current_logger().info("Before test:" + semanage.get("stdout", ""))
    except CalledProcessError as e:
        api.current_logger().warning("Error listing SELinux customizations: %s", str(e.stderr))

    semodule_list = [SELinuxModule(name=module, priority=int(prio), content="", removed=[])
                     for (prio, module) in test_modules + [["400", "permissive_abrt_t"]]]

    current_actor_context.feed(SELinuxModules(modules=semodule_list))
    current_actor_context.run()

    # check if all given modules and local customizations where removed
    try:
        semodule = run(["semodule", "-lfull"], split=False)
        assert semodule_lfull == semodule.get("stdout", "")
        semanage = run(["semanage", "export"], split=False)
        assert semanage_export == semanage.get("stdout", "")
    except CalledProcessError as e:
        api.current_logger().warning("Error listing SELinux customizations: %s", str(e.stderr))
        assert False


def teardown():
    if enabled:
        for priority, module in test_modules + [["400", "permissive_abrt_t"]]:
            try:
                run(["semodule", "-X", priority, "-r", module])
            except CalledProcessError:
                # expected -- should be removed by the actor
                pass

        for command in semanage_commands:
            try:
                run(["semanage", command[0], "-d"] + command[1:])
            except CalledProcessError:
                # expected -- should be removed by the actor
                continue
