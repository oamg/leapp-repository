import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import scandnfcomps
from leapp.libraries.common.dnflibs import DNFRepoError
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import DNFEnvironment, DNFGroup, InstalledDNFComps


class MockCompsGroup():
    def __init__(self, gid, ui_name):
        self.id = gid
        self.ui_name = ui_name


class MockCompsEnvironment():
    def __init__(self, env_id, ui_name):
        self.id = env_id
        self.ui_name = ui_name


class MockComps():
    def __init__(self, groups=None, environments=None):
        self._groups = groups or []
        self._environments = environments or []

    def groups_iter(self):
        return iter(self._groups)

    def environments_iter(self):
        return iter(self._environments)


class MockHistory():

    class _Lookup():
        """
        Simulates base.history.group or base.history.env

        group & env have have same "API" that we use, so no need to create
        a different class for each one.
        """

        def __init__(self, installed_ids):
            self._installed = set(installed_ids)

        def get(self, item_id):
            return item_id in self._installed

    def __init__(self, installed_group_ids=None, installed_env_ids=None):
        self.group = MockHistory._Lookup(installed_group_ids or [])
        self.env = MockHistory._Lookup(installed_env_ids or [])


class MockDNFBase():
    def __init__(self, comps=None, history=None):
        self.comps = comps or MockComps()
        self.history = history or MockHistory()


def test_process_with_groups_and_environments(monkeypatch):
    comps = MockComps(
        groups=[
            MockCompsGroup('core', 'Core'),
            MockCompsGroup('base', 'Base'),
        ],
        environments=[
            MockCompsEnvironment('minimal-environment', 'Minimal Install'),
        ],
    )
    history = MockHistory(
        installed_group_ids=['core', 'base'],
        installed_env_ids=['minimal-environment'],
    )
    base = MockDNFBase(comps=comps, history=history)

    mocked_producer = produce_mocked()
    monkeypatch.setattr(scandnfcomps, 'create_dnf_base', lambda: base)
    monkeypatch.setattr(scandnfcomps, 'dnf', True)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', mocked_producer)

    scandnfcomps.process()

    assert mocked_producer.called == 1
    msg = mocked_producer.model_instances[0]
    assert isinstance(msg, InstalledDNFComps)
    assert len(msg.groups) == 2
    assert msg.groups[0].id == 'base'
    assert msg.groups[0].name == 'Base'
    assert msg.groups[1].id == 'core'
    assert msg.groups[1].name == 'Core'
    assert len(msg.environments) == 1
    assert msg.environments[0].id == 'minimal-environment'
    assert msg.environments[0].name == 'Minimal Install'


def test_process_filters_not_installed(monkeypatch):
    """Only groups/environments recorded as installed in history are returned."""
    comps = MockComps(
        groups=[
            MockCompsGroup('core', 'Core'),
            MockCompsGroup('base', 'Base'),
            MockCompsGroup('extra', 'Extra'),
        ],
        environments=[
            MockCompsEnvironment('minimal-environment', 'Minimal Install'),
            MockCompsEnvironment('server-product-environment', 'Server'),
        ],
    )
    history = MockHistory(
        installed_group_ids=['core'],
        installed_env_ids=['server-product-environment'],
    )
    base = MockDNFBase(comps=comps, history=history)

    mocked_producer = produce_mocked()
    monkeypatch.setattr(scandnfcomps, 'create_dnf_base', lambda: base)
    monkeypatch.setattr(scandnfcomps, 'dnf', True)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', mocked_producer)

    scandnfcomps.process()

    assert mocked_producer.called == 1
    msg = mocked_producer.model_instances[0]
    assert len(msg.groups) == 1
    assert msg.groups[0].id == 'core'
    assert len(msg.environments) == 1
    assert msg.environments[0].id == 'server-product-environment'


def test_process_empty_comps(monkeypatch):
    base = MockDNFBase()

    mocked_producer = produce_mocked()
    monkeypatch.setattr(scandnfcomps, 'create_dnf_base', lambda: base)
    monkeypatch.setattr(scandnfcomps, 'dnf', True)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', mocked_producer)

    scandnfcomps.process()

    assert mocked_producer.called == 1
    msg = mocked_producer.model_instances[0]
    assert isinstance(msg, InstalledDNFComps)
    assert msg.groups == []
    assert msg.environments == []


def test_process_no_dnf(monkeypatch):
    mocked_producer = produce_mocked()
    monkeypatch.setattr(scandnfcomps, 'dnf', None)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', mocked_producer)

    scandnfcomps.process()
    assert mocked_producer.called == 0


def test_process_dnf_repo_error(monkeypatch):
    def raise_repo_error():
        raise DNFRepoError(
            message='DNF failed to load repositories: repo error',
            details={'hint': 'Ensure the myrepo repository definition is correct.'}
        )

    monkeypatch.setattr(scandnfcomps, 'create_dnf_base', raise_repo_error)
    monkeypatch.setattr(scandnfcomps, 'dnf', True)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())

    with pytest.raises(StopActorExecutionError, match='Cannot obtain information about DNF Groups and Environments'):
        scandnfcomps.process()
