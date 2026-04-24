import pytest

from leapp.libraries.common.dnflibs import dnfconfig
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError


class MockContext:
    def __init__(self, stdout=None, should_raise=None):
        self.stdout = stdout or []
        self.should_raise = should_raise
        self.commands = []

    @property
    def last_cmd(self):
        return self.commands[-1] if self.commands else None

    def call(self, cmd, split=False):
        self.commands.append(cmd)
        if self.should_raise:
            raise self.should_raise
        if split:
            return {'stdout': self.stdout}
        # TODO(pstodulk): this part is not used now, but if we want to make
        # this in future more generic, we should update it properly
        return None


_SAMPLE_DNF_DUMP = [
    '[main]',
    'gpgcheck = 1',
    'installonly_limit = 3',
    'clean_requirements_on_remove = True',
    'exclude = pkg1,pkg2',
]


@pytest.mark.parametrize('data,sep,maxsplit,expected', [
    ('key = value', '=', -1, ['key', 'value']),
    ('  key  =  value  ', '=', -1, ['key', 'value']),
    ('a,b,c,d', ',', 2, ['a', 'b', 'c,d']),
    ('pkg1, pkg2, pkg3', ',', -1, ['pkg1', 'pkg2', 'pkg3']),
])
def test_strip_split(data, sep, maxsplit, expected):
    result = dnfconfig._strip_split(data, sep, maxsplit)
    assert result == expected


def test_get_main_dump_success(monkeypatch):
    context = MockContext(stdout=_SAMPLE_DNF_DUMP)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    result = dnfconfig._get_main_dump(context, disable_plugins=None)

    assert 'gpgcheck' in result
    assert result['gpgcheck'] == '1'
    assert result['installonly_limit'] == '3'
    assert result['exclude'] == 'pkg1,pkg2'


def test_get_main_dump_with_disabled_plugins():
    context = MockContext(stdout=_SAMPLE_DNF_DUMP)

    dnfconfig._get_main_dump(context, disable_plugins=['plugin1', 'plugin2'])

    expected_cmd = [
        'dnf', 'config-manager', '--dump',
        '--disableplugin', 'plugin1',
        '--disableplugin', 'plugin2'
    ]
    assert context.last_cmd == expected_cmd


def test_get_main_dump_command_fails(monkeypatch):
    err = CalledProcessError(
        'Command failed',
        ['dnf', 'config-manager', '--dump'],
        {'stdout': 'stdout output', 'stderr': 'stderr output', 'exit_code': 1}
    )
    context = MockContext(should_raise=err)

    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    with pytest.raises(dnfconfig.CannotObtainDNFConfig) as exc_info:
        dnfconfig._get_main_dump(context, disable_plugins=None)

    assert 'Cannot obtain data about the DNF configuration' in str(exc_info.value)
    assert exc_info.value.details['stdout'] == 'stdout output'
    assert exc_info.value.details['stderr'] == 'stderr output'


def test_get_main_dump_missing_main_section():
    stdout = [
        '[repo1]',
        'name = Repository 1',
        'enabled = 1'
    ]
    context = MockContext(stdout=stdout)

    with pytest.raises(dnfconfig.InvalidDNFConfig) as exc_info:
        dnfconfig._get_main_dump(context, disable_plugins=None)

    assert 'Invalid DNF configuration data (missing [main])' in str(exc_info.value)


def test_get_main_dump_malformed_line(monkeypatch):
    stdout = [
        '[main]',
        'gpgcheck = 1',
        'malformed line without equals',
        'exclude = pkg1'
    ]
    context = MockContext(stdout=stdout)

    mocked_logger = logger_mocked()
    monkeypatch.setattr(api, 'current_logger', mocked_logger)

    result = dnfconfig._get_main_dump(context, disable_plugins=None)

    assert result['gpgcheck'] == '1'
    assert result['exclude'] == 'pkg1'
    assert len(mocked_logger.warnmsg) > 0
    assert 'malformed line without equals' in mocked_logger.warnmsg[0]


@pytest.mark.parametrize('exclude_value,expected', [
    ('pkg1, pkg2, pkg3', ['pkg1', 'pkg2', 'pkg3']),
    ('pkg1,pkg2,  pkg3', ['pkg1', 'pkg2', 'pkg3']),
    ('', []),
    ('pkg1,  , pkg2,  ', ['pkg1', 'pkg2']),
])
def test_get_excluded_pkgs(exclude_value, expected):
    stdout = ['[main]', 'exclude = {}'.format(exclude_value)] if exclude_value else ['[main]', 'gpgcheck = 1']
    context = MockContext(stdout=stdout)

    result = dnfconfig._get_excluded_pkgs(context, disable_plugins=None)

    assert result == expected


def test_set_excluded_pkgs_success():
    context = MockContext()
    pkglist = ['pkg1', 'pkg2', 'pkg3']

    dnfconfig._set_excluded_pkgs(context, pkglist, disable_plugins=None)

    expected_cmd = [
        'dnf', 'config-manager', '--save',
        '--setopt', 'exclude=pkg1,pkg2,pkg3'
    ]
    assert context.last_cmd == expected_cmd


def test_set_excluded_pkgs_with_disabled_plugins():
    context = MockContext()

    dnfconfig._set_excluded_pkgs(context, ['pkg1'], disable_plugins=['plugin1', 'plugin2'])

    expected_cmd = [
        'dnf', 'config-manager', '--save',
        '--setopt', 'exclude=pkg1',
        '--disableplugin', 'plugin1',
        '--disableplugin', 'plugin2'
    ]
    assert context.last_cmd == expected_cmd


def test_set_excluded_pkgs_fails(monkeypatch):
    err = CalledProcessError(
        'Command failed',
        ['dnf', 'config-manager', '--save'],
        {'stdout': 'stdout output', 'stderr': 'stderr output', 'exit_code': 1}
    )
    context = MockContext(should_raise=err)

    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    with pytest.raises(dnfconfig.CannotUpdateDNFConfig) as exc_info:
        dnfconfig._set_excluded_pkgs(context, ['pkg1'], disable_plugins=None)

    assert 'Cannot update the DNF configuration' in str(exc_info.value)
    assert exc_info.value.details['stdout'] == 'stdout output'
    assert exc_info.value.details['stderr'] == 'stderr output'


def test_exclude_leapp_rpms(monkeypatch):
    """
    Test that exclude_leapp_rpms merges existing exclusions with leapp packages
    """
    context = MockContext(stdout=[
        '[main]',
        'exclude = existing-pkg1, existing-pkg2'
    ])
    monkeypatch.setattr(dnfconfig, 'get_leapp_packages', lambda: ['leapp', 'leapp-upgrade-el8toel9'])

    dnfconfig.exclude_leapp_rpms(context, disable_plugins=None)

    setopt_cmd = None
    for cmd in context.commands:
        if '--setopt' in cmd:
            setopt_cmd = cmd
            break

    assert setopt_cmd is not None
    exclude_arg = set([arg for arg in setopt_cmd if arg.startswith('exclude=')][0].split('=')[1].split(','))
    expected_arg = set(['existing-pkg1', 'existing-pkg2', 'leapp', 'leapp-upgrade-el8toel9'])
    assert expected_arg == exclude_arg


def test_exclude_leapp_rpms_no_duplicates(monkeypatch):
    context = MockContext(stdout=[
        '[main]',
        'exclude = leapp'
    ])
    monkeypatch.setattr(dnfconfig, 'get_leapp_packages', lambda: ['leapp', 'leapp-upgrade-el8toel9'])

    dnfconfig.exclude_leapp_rpms(context, disable_plugins=None)

    setopt_cmd = None
    for cmd in context.commands:
        if '--setopt' in cmd:
            setopt_cmd = cmd
            break

    assert setopt_cmd is not None
    exclude_arg = [arg for arg in setopt_cmd if arg.startswith('exclude=')][0]
    packages = exclude_arg.replace('exclude=', '').split(',')
    assert packages.count('leapp') == 1
