import pytest

from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp.libraries.actor import tus_targetrepos
from leapp.libraries.common import repofileutils
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    CustomTargetRepository,
    DistroTargetRepository,
    RepositoriesFactsTarget,
    RepositoryData,
    RepositoryFile,
    RHELTargetRepository,
    TargetRepositories,
    UsedTargetRepositories
)


class MockContext:
    """Opaque context sentinel - all context consumers are monkeypatched."""


class MockInputData:
    def __init__(self, target_repositories, rhui_info=None, skip_rhsm=False):
        self.target_repositories = target_repositories
        self.rhui_info = rhui_info
        self.skip_rhsm = skip_rhsm


class MockRepoListHolder:
    """Lightweight stand-in used to exercise the ``or []`` None handling."""

    def __init__(self, distro_repos=None, rhel_repos=None, custom_repos=None):
        self.distro_repos = distro_repos
        self.rhel_repos = rhel_repos
        self.custom_repos = custom_repos


def _repofile(filename, repoids):
    return RepositoryFile(
        file=filename,
        data=[RepositoryData(repoid=repoid, name=repoid) for repoid in repoids]
    )


def _target_repositories(distro=None, custom=None, rhel=None):
    return TargetRepositories(
        rhel_repos=[RHELTargetRepository(repoid=repoid) for repoid in (rhel or [])],
        distro_repos=[DistroTargetRepository(repoid=repoid) for repoid in (distro or [])],
        custom_repos=[CustomTargetRepository(repoid=repoid) for repoid in (custom or [])],
    )


def _make_distro_repoids(repoids):
    def _fake(_context):
        return list(repoids)
    return _fake


def _make_rhui_repoids(repoids):
    def _fake(_context, _rhui_info, _target_version):
        return set(repoids)
    return _fake


def _make_repofiles(repofiles):
    def _fake(_context):
        return repofiles
    return _fake


def _raise_invalid_repofiles(_context):
    raise repofileutils.InvalidRepoDefinition('broken', repofile='f.repo', repoid='rid')


@pytest.fixture(autouse=True)
def _default_api(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())


@pytest.fixture
def mocked_reports(monkeypatch):
    mock = create_report_mocked()
    monkeypatch.setattr(tus_targetrepos.reporting, 'create_report', mock)
    return mock


def test_requested_distro_repoids_union():
    target_repositories = _target_repositories(distro=['a', 'b'], rhel=['c'])
    assert tus_targetrepos._requested_distro_repoids(target_repositories) == {'a', 'b', 'c'}


def test_requested_distro_repoids_none():
    assert tus_targetrepos._requested_distro_repoids(MockRepoListHolder()) == set()


def test_requested_custom_repoids():
    target_repositories = _target_repositories(custom=['x', 'y'])
    assert tus_targetrepos._requested_custom_repoids(target_repositories) == {'x', 'y'}


def test_requested_custom_repoids_none():
    assert tus_targetrepos._requested_custom_repoids(MockRepoListHolder()) == set()


def test_all_available_repoids(monkeypatch):
    repofiles = [
        _repofile('a.repo', ['baseos', 'appstream']),
        _repofile('b.repo', ['custom']),
    ]
    monkeypatch.setattr(repofileutils, 'get_parsed_repofiles', _make_repofiles(repofiles))
    assert tus_targetrepos._all_available_repoids(MockContext()) == {'baseos', 'appstream', 'custom'}


@pytest.mark.parametrize(
    ('repofiles_spec', 'expected'),
    [
        ([('a.repo', ['one', 'two'])], set()),
        ([('a.repo', ['dup']), ('b.repo', ['dup'])], {'dup'}),
        ([('a.repo', ['dup', 'dup'])], {'dup'}),
        ([('a.repo', ['one', 'dup']), ('b.repo', ['dup', 'two'])], {'dup'}),
    ]
)
def test_duplicate_repoids(monkeypatch, repofiles_spec, expected):
    repofiles = [_repofile(name, repoids) for name, repoids in repofiles_spec]
    monkeypatch.setattr(repofileutils, 'get_parsed_repofiles', _make_repofiles(repofiles))
    assert tus_targetrepos._duplicate_repoids(MockContext()) == expected


@pytest.mark.parametrize(
    ('repoids', 'expected'),
    [
        (['baseos', 'appstream'], True),
        (['BaseOS-9', 'AppStream-9'], True),
        (['rhel-9-baseos-rpms', 'rhel-9-appstream-rpms'], True),
        (['appstream'], False),
        (['baseos'], False),
        ([], False),
        (['foo', 'bar'], False),
    ]
)
def test_has_base_repos(repoids, expected):
    assert tus_targetrepos._has_base_repos(repoids) is expected


@pytest.mark.parametrize(
    ('src_distro', 'dst_distro', 'src_ver', 'skip_rhsm', 'expected'),
    [
        ('centos', 'rhel', '8.10', False, False),    # conversion
        ('centos', 'centos', '8.10', False, False),  # source CentOS Stream 8
        ('rhel', 'rhel', '8.10', True, False),       # RHEL target + skip rhsm
        ('rhel', 'rhel', '8.10', False, True),       # default: check applies
        ('centos', 'centos', '9.6', True, True),     # not cs8, non-rhel target
    ]
)
def test_base_repo_check_applies(monkeypatch, src_distro, dst_distro, src_ver, skip_rhsm, expected):
    monkeypatch.setattr(
        api, 'current_actor',
        CurrentActorMocked(src_ver=src_ver, src_distro=src_distro, dst_distro=dst_distro)
    )
    assert tus_targetrepos._base_repo_check_applies(skip_rhsm) is expected


def test_inhibit_no_base_repos_rhel(monkeypatch, mocked_reports):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_distro='rhel'))
    tus_targetrepos._inhibit_no_base_repos('9')
    assert mocked_reports.called == 1
    report = mocked_reports.report_fields
    assert report['title'] == 'Cannot find required basic target OS repositories.'
    assert 'inhibitor' in report['groups']
    assert 'remediations' in report['detail']


def test_inhibit_no_base_repos_non_rhel(monkeypatch, mocked_reports):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_distro='centos'))
    tus_targetrepos._inhibit_no_base_repos('9')
    assert mocked_reports.called == 1
    report = mocked_reports.report_fields
    assert report['title'] == 'Cannot find required basic target OS repositories.'
    assert 'remediations' not in report.get('detail', {})


def test_inhibit_missing_custom_repos(mocked_reports):
    tus_targetrepos._inhibit_missing_custom_repos(['missing-repo'])
    assert mocked_reports.called == 1
    report = mocked_reports.report_fields
    assert report['title'] == 'Some required custom target repositories have not been found'
    assert 'inhibitor' in report['groups']


def test_inhibit_no_enabled_target_repos(mocked_reports):
    tus_targetrepos._inhibit_no_enabled_target_repos('9.6')
    assert mocked_reports.called == 1
    report = mocked_reports.report_fields
    assert report['title'] == 'There are no enabled target repositories'
    assert 'inhibitor' in report['groups']


def test_inhibit_duplicate_repos(mocked_reports):
    tus_targetrepos._inhibit_duplicate_repos(['dup'])
    assert mocked_reports.called == 1
    report = mocked_reports.report_fields
    assert report['title'] == 'A YUM/DNF repository defined multiple times'
    assert 'inhibitor' in report['groups']


def _setup_discovery(monkeypatch, distro_repoids, rhui_repoids=None):
    monkeypatch.setattr(
        tus_targetrepos.distro, 'get_target_distro_repoids', _make_distro_repoids(distro_repoids)
    )
    monkeypatch.setattr(
        tus_targetrepos.tus_rhui, 'discover_client_exposed_repoids',
        _make_rhui_repoids(rhui_repoids or set())
    )


def test_select_target_repositories_no_base_repos(monkeypatch, mocked_reports):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_distro='rhel', dst_distro='rhel'))
    _setup_discovery(monkeypatch, {'notbase'})
    inputs = MockInputData(_target_repositories(distro=['notbase']), skip_rhsm=False)

    with pytest.raises(StopActorExecution):
        tus_targetrepos.select_target_repositories(MockContext(), inputs)

    assert mocked_reports.called == 1
    assert mocked_reports.report_fields['title'] == 'Cannot find required basic target OS repositories.'


def test_select_target_repositories_no_enabled(monkeypatch, mocked_reports):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_distro='rhel', dst_distro='rhel'))
    _setup_discovery(monkeypatch, set())
    monkeypatch.setattr(repofileutils, 'get_parsed_repofiles', _make_repofiles([]))
    inputs = MockInputData(_target_repositories(), skip_rhsm=True)

    with pytest.raises(StopActorExecution):
        tus_targetrepos.select_target_repositories(MockContext(), inputs)

    assert mocked_reports.called == 1
    assert mocked_reports.report_fields['title'] == 'There are no enabled target repositories'


def test_select_target_repositories_missing_custom(monkeypatch, mocked_reports):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_distro='rhel', dst_distro='rhel'))
    _setup_discovery(monkeypatch, {'baseos', 'appstream'})
    repofiles = [_repofile('a.repo', ['baseos', 'appstream'])]
    monkeypatch.setattr(repofileutils, 'get_parsed_repofiles', _make_repofiles(repofiles))
    inputs = MockInputData(
        _target_repositories(distro=['baseos', 'appstream'], custom=['missing']),
        skip_rhsm=False
    )

    with pytest.raises(StopActorExecution):
        tus_targetrepos.select_target_repositories(MockContext(), inputs)

    assert mocked_reports.called == 1
    assert mocked_reports.report_fields['title'] == 'Some required custom target repositories have not been found'


def test_select_target_repositories_duplicates_when_skip_rhsm(monkeypatch, mocked_reports):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_distro='rhel', dst_distro='rhel'))
    _setup_discovery(monkeypatch, set())
    repofiles = [
        _repofile('a.repo', ['myrepo', 'dup']),
        _repofile('b.repo', ['dup']),
    ]
    monkeypatch.setattr(repofileutils, 'get_parsed_repofiles', _make_repofiles(repofiles))
    inputs = MockInputData(_target_repositories(custom=['myrepo']), skip_rhsm=True)

    result = tus_targetrepos.select_target_repositories(MockContext(), inputs)

    assert mocked_reports.called == 1
    assert mocked_reports.report_fields['title'] == 'A YUM/DNF repository defined multiple times'
    assert [repo.repoid for repo in result.repos] == ['myrepo']


def test_select_target_repositories_success(monkeypatch, mocked_reports):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_distro='rhel', dst_distro='rhel'))
    _setup_discovery(monkeypatch, {'baseos', 'appstream'})
    repofiles = [_repofile('a.repo', ['baseos', 'appstream', 'mycustom'])]
    monkeypatch.setattr(repofileutils, 'get_parsed_repofiles', _make_repofiles(repofiles))
    inputs = MockInputData(
        _target_repositories(distro=['baseos', 'appstream'], custom=['mycustom']),
        skip_rhsm=False
    )

    result = tus_targetrepos.select_target_repositories(MockContext(), inputs)

    assert isinstance(result, UsedTargetRepositories)
    assert [repo.repoid for repo in result.repos] == ['appstream', 'baseos', 'mycustom']
    assert mocked_reports.called == 0


def test_select_target_repositories_invalid_repo_definition(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_distro='rhel', dst_distro='rhel'))
    _setup_discovery(monkeypatch, set())
    monkeypatch.setattr(repofileutils, 'get_parsed_repofiles', _raise_invalid_repofiles)
    inputs = MockInputData(_target_repositories(), skip_rhsm=True)

    with pytest.raises(StopActorExecutionError):
        tus_targetrepos.select_target_repositories(MockContext(), inputs)


def test_build_target_repositories_snapshot(monkeypatch):
    repofiles = [_repofile('a.repo', ['baseos']), _repofile('b.repo', ['appstream'])]
    monkeypatch.setattr(repofileutils, 'get_parsed_repofiles', _make_repofiles(repofiles))

    result = tus_targetrepos.build_target_repositories_snapshot(MockContext())

    assert isinstance(result, RepositoriesFactsTarget)
    assert [repofile.file for repofile in result.repositories] == ['a.repo', 'b.repo']


def test_build_target_repositories_snapshot_invalid(monkeypatch):
    monkeypatch.setattr(repofileutils, 'get_parsed_repofiles', _raise_invalid_repofiles)

    with pytest.raises(StopActorExecutionError):
        tus_targetrepos.build_target_repositories_snapshot(MockContext())
