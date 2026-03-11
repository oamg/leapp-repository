"""
Trivial unit testing of dnfmodule library => keeping it on integration tests.

There is actually not a good coverage we could do for this library via
unit-tests. These tests seem to have a low value at all as there is no
a good way to cover this library without complete mocking of actually whole
DNF & hawkey libs. At this point, we keep focus on integration tests executed
in CI pipelines.

I am still keeping these unit-tests present for an elementary functionality
check - but mainly because I expect low maintenance cost for them as the library
is kind of finished - we can expect minimal changes in future until its removal.
"""

from leapp.libraries.common.dnflibs import dnfmodule


class MockModulePackage:
    def __init__(self, name, stream, artifacts=None):
        self._name = name
        self._stream = stream
        self._artifacts = artifacts or []

    def getName(self):
        return self._name

    def getStream(self):
        return self._stream

    def getArtifacts(self):
        return self._artifacts


class MockNEVRA:
    def __init__(self, name, version, release, arch):
        self.name = name
        self.version = version
        self.release = release
        self.arch = arch


class MockModuleBase:
    def __init__(self, base):
        self.base = base
        self._modules = []

    def get_modules(self, pattern):
        return [self._modules, None]


class MockModuleContainer:
    def __init__(self):
        self._enabled = set()

    def isEnabled(self, module):
        return module.getName() in self._enabled

    def enable(self, module_name):
        self._enabled.add(module_name)


class MockSack:
    def __init__(self):
        self._moduleContainer = MockModuleContainer()


class MockDNFBase:
    def __init__(self):
        self.sack = MockSack()


def _split_nevra(rpm_str):
    """Simple NEVRA parser for testing"""
    parts = rpm_str.rsplit('.', 1)
    arch = parts[-1] if len(parts) > 1 else 'noarch'
    rest = parts[0] if len(parts) > 1 else rpm_str

    parts = rest.rsplit('-', 2)
    if len(parts) >= 3:
        name, version, release = parts[0], parts[1], parts[2]
    elif len(parts) == 2:
        name, version, release = parts[0], parts[1], '0'
    else:
        name, version, release = parts[0], '0', '0'

    return MockNEVRA(name, version, release, arch)


def test_get_modules_with_base(monkeypatch):
    module1 = MockModulePackage('nodejs', '18')
    module2 = MockModulePackage('postgresql', '15')

    base = MockDNFBase()

    class ModuleBaseWithModules(MockModuleBase):
        def __init__(self, base):
            super().__init__(base)
            self._modules = [module1, module2]

    class MockDNF:
        class module:
            class module_base:
                ModuleBase = ModuleBaseWithModules

    monkeypatch.setattr(dnfmodule, 'dnf', MockDNF)

    modules = dnfmodule.get_modules(base)

    assert len(modules) == 2
    assert modules[0].getName() == 'nodejs'
    assert modules[1].getName() == 'postgresql'


def test_get_modules_without_base(monkeypatch):
    module1 = MockModulePackage('nodejs', '18')

    def mock_create_dnf_base():
        return MockDNFBase()

    class ModuleBaseWithModules(MockModuleBase):
        def __init__(self, base):
            super().__init__(base)
            self._modules = [module1]

    class MockDNF:
        class module:
            class module_base:
                ModuleBase = ModuleBaseWithModules

    monkeypatch.setattr(dnfmodule, 'create_dnf_base', mock_create_dnf_base)
    monkeypatch.setattr(dnfmodule, 'dnf', MockDNF)

    modules = dnfmodule.get_modules()

    assert len(modules) == 1
    assert modules[0].getName() == 'nodejs'


def test_get_modules_no_get_modules_method(monkeypatch):
    """
    Test the compatibility for DNF versions without module stream functionality.

    This is know a case for RHEL 7, which we do not support in upstream anymore.
    However, it's possible that future versions of DNF will drop module stream
    functionality as well. So keeping this test for now, but the functionality
    can be "broken" in different ways from the one we test at this moment.
    """
    base = MockDNFBase()

    class LimitedModuleBase:
        def __init__(self, base):
            self.base = base

    class MockDNF:
        class module:
            class module_base:
                ModuleBase = LimitedModuleBase

    monkeypatch.setattr(dnfmodule, 'dnf', MockDNF)

    modules = dnfmodule.get_modules(base)

    assert modules == []


def test_get_enabled_modules(monkeypatch):
    module1 = MockModulePackage('nodejs', '18')
    module2 = MockModulePackage('postgresql', '15')
    module3 = MockModulePackage('ruby', '3.0')

    def mock_create_dnf_base():
        base = MockDNFBase()
        base.sack._moduleContainer.enable('nodejs')
        base.sack._moduleContainer.enable('ruby')
        return base

    class ModuleBaseWithModules(MockModuleBase):
        def __init__(self, base):
            super().__init__(base)
            self._modules = [module1, module2, module3]

    class MockDNF:
        class module:
            class module_base:
                ModuleBase = ModuleBaseWithModules

    monkeypatch.setattr(dnfmodule, 'create_dnf_base', mock_create_dnf_base)
    monkeypatch.setattr(dnfmodule, 'dnf', MockDNF)

    enabled = dnfmodule.get_enabled_modules()

    assert len(enabled) == 2
    enabled_names = [m.getName() for m in enabled]
    assert 'nodejs' in enabled_names
    assert 'ruby' in enabled_names
    assert 'postgresql' not in enabled_names


def test_get_enabled_modules_no_dnf(monkeypatch):
    monkeypatch.setattr(dnfmodule, 'dnf', None)

    enabled = dnfmodule.get_enabled_modules()

    assert enabled == []


def test_map_installed_rpms_to_modules(monkeypatch):
    module1 = MockModulePackage('nodejs', '18', artifacts=[
        'nodejs-18.0.0-1.x86_64',
        'npm-8.0.0-1.x86_64'
    ])
    module2 = MockModulePackage('postgresql', '15', artifacts=[
        'postgresql-15.0-1.x86_64',
        'postgresql-server-15.0-1.x86_64'
    ])

    class ModuleBaseWithModules(MockModuleBase):
        def __init__(self, base):
            super().__init__(base)
            self._modules = [module1, module2]

    class MockDNF:
        class module:
            class module_base:
                ModuleBase = ModuleBaseWithModules

    class MockHawkey:
        split_nevra = staticmethod(_split_nevra)

    def mock_create_dnf_base():
        return MockDNFBase()

    monkeypatch.setattr(dnfmodule, 'create_dnf_base', mock_create_dnf_base)
    monkeypatch.setattr(dnfmodule, 'dnf', MockDNF)
    monkeypatch.setattr(dnfmodule, 'hawkey', MockHawkey)

    rpm_map = dnfmodule.map_installed_rpms_to_modules()

    assert ('nodejs', '18.0.0', '1', 'x86_64') in rpm_map
    assert rpm_map[('nodejs', '18.0.0', '1', 'x86_64')] == ('nodejs', '18')

    assert ('npm', '8.0.0', '1', 'x86_64') in rpm_map
    assert rpm_map[('npm', '8.0.0', '1', 'x86_64')] == ('nodejs', '18')

    assert ('postgresql', '15.0', '1', 'x86_64') in rpm_map
    assert rpm_map[('postgresql', '15.0', '1', 'x86_64')] == ('postgresql', '15')

    assert ('postgresql-server', '15.0', '1', 'x86_64') in rpm_map
    assert rpm_map[('postgresql-server', '15.0', '1', 'x86_64')] == ('postgresql', '15')


def test_map_installed_rpms_to_modules_empty(monkeypatch):
    class EmptyModuleBase(MockModuleBase):
        def __init__(self, base):
            super().__init__(base)
            self._modules = []

    class MockDNF:
        class module:
            class module_base:
                ModuleBase = EmptyModuleBase

    class MockHawkey:
        split_nevra = staticmethod(_split_nevra)

    def mock_create_dnf_base():
        return MockDNFBase()

    monkeypatch.setattr(dnfmodule, 'create_dnf_base', mock_create_dnf_base)
    monkeypatch.setattr(dnfmodule, 'dnf', MockDNF)
    monkeypatch.setattr(dnfmodule, 'hawkey', MockHawkey)

    rpm_map = dnfmodule.map_installed_rpms_to_modules()

    assert rpm_map == {}
