import os

import pytest

from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import SELinuxModule, SELinuxModules
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context

TEST_MODULES = [
    ['400', 'mock1'],
    ['99', 'mock1'],
    ['300', 'mock1'],
    ['400', 'mock2'],
    ['999', 'mock3'],
]

TEST_TEMPLATES = [
    ['200', 'base_container']
]

SEMANAGE_COMMANDS = [
    ['fcontext', '-t', 'httpd_sys_content_t', '"/web(/.*)?"'],
    ['fcontext', '-t', 'cgdcbxd_var_run_t', '"/ganesha(/.*)?"'],
    ['fcontext', '-t', 'mock_file_type_t', '"/mock_directory(/.*)?"'],
    ['port', '-t', 'http_port_t', '-p', 'udp', '81'],
    ['permissive', 'abrt_t']
]

testmoduledir = 'tests/mock_modules/'


def _run_cmd(cmd, logmsg='', split=False):
    try:
        return run(cmd, split=split).get('stdout', '')
    except CalledProcessError as e:
        if logmsg:
            api.current_logger().warning('{}: {}'.format(logmsg, e.stderr))
    return None


@pytest.fixture(scope='module')
def semodule_lfull_initial():
    yield _run_cmd(['semodule', '-lfull'], logmsg='Error listing SELinux customizations')


@pytest.fixture(scope='module')
def semanage_export_initial():
    yield _run_cmd(['semanage', 'export'], logmsg='Error listing SELinux customizations')


@pytest.fixture(scope='function')
def destructive_selinux_env():
    tests_dir = os.path.join(os.getenv('PYTEST_CURRENT_TEST').rsplit(os.path.sep, 2)[0], testmoduledir)

    # try to install compatibility module - needed on newer systems - failure to install is expected on rhel 7
    _run_cmd(['semodule', '-X', '100', '-i', os.path.join(tests_dir, 'compat.cil')])

    semodule_command = ['semodule']
    for priority, module in TEST_MODULES + TEST_TEMPLATES:
        semodule_command.extend(['-X', priority, '-i', os.path.join(tests_dir, module + '.cil')])
    _run_cmd(semodule_command, logmsg='Error installing mock modules')

    for command in SEMANAGE_COMMANDS:
        _run_cmd(['semanage', command[0], '-a'] + command[1:], logmsg='Error applying selinux customizations')

    yield

    for command in SEMANAGE_COMMANDS:
        _run_cmd(['semanage', command[0], '-d'] + command[1:])

    semodule_command = ['semodule']
    for priority, module in reversed(TEST_MODULES + TEST_TEMPLATES +
                                     [['400', 'permissive_abrt_t'], ['100', 'compat']]):
        semodule_command.extend(['-X', priority, '-r', module])
    _run_cmd(semodule_command)


@pytest.mark.skipif(os.getenv('DESTRUCTIVE_TESTING', False) in [False, '0'],
                    reason='Test disabled by default because it would modify the system')
def test_SELinuxPrepare(current_actor_context, semodule_lfull_initial, semanage_export_initial,
                        destructive_selinux_env):
    before_test = []
    for cmd in (['semodule', '-lfull'], ['semanage', 'export']):
        res = _run_cmd(cmd, 'Error listing SELinux customizations')
        before_test.append(res)
        # XXX still not sure about logging in tests
        api.current_logger().info('Before test: {}'.format(res))
    # Make sure that initial semodule/semanage commands don't match before tests ones
    assert before_test != [semodule_lfull_initial, semanage_export_initial]

    semodule_list = [SELinuxModule(name=module, priority=int(prio), content='', removed=[])
                     for (prio, module) in TEST_MODULES + [['400', 'permissive_abrt_t'], ['100', 'compat']]]

    template_list = [SELinuxModule(name=module, priority=int(prio), content='', removed=[])
                     for (prio, module) in TEST_TEMPLATES]

    current_actor_context.feed(SELinuxModules(modules=semodule_list, templates=template_list))

    current_actor_context.run()

    # check if all given modules and local customizations where removed
    semodule_res = _run_cmd(['semodule', '-lfull'], 'Error listing SELinux modules')
    assert semodule_lfull_initial == semodule_res
    semanage_res = _run_cmd(['semanage', 'export'], 'Error listing SELinux customizations')
    assert semanage_export_initial == semanage_res
