import os
from collections import namedtuple

import pytest

from leapp import models, reporting
from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp.libraries.actor import userspacegen
from leapp.libraries.common import overlaygen, repofileutils, rhsm
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.utils.deprecation import suppress_deprecation

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
_CERTS_PATH = os.path.join(CUR_DIR, '../../../files', userspacegen.PROD_CERTS_FOLDER)
_DEFAULT_CERT_PATH = os.path.join(_CERTS_PATH, '8.1', '479.pem')


@pytest.fixture
def adjust_cwd():
    previous_cwd = os.getcwd()
    os.chdir(os.path.join(CUR_DIR, "../"))
    yield
    os.chdir(previous_cwd)


class MockedMountingBase(object):
    def __init__(self, **dummy_kwargs):
        self.called_copytree_from = []
        self.target = ''

    def copytree_from(self, src, dst):
        self.called_copytree_from.append((src, dst))

    def __call__(self, **dummy_kwarg):
        yield self

    def call(self, *args, **kwargs):
        return {'stdout': ''}

    def nspawn(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        pass


@pytest.mark.parametrize('result,dst_ver,arch,prod_type', [
    (os.path.join(_CERTS_PATH, '8.1', '479.pem'), '8.1', architecture.ARCH_X86_64, 'ga'),
    (os.path.join(_CERTS_PATH, '8.1', '419.pem'), '8.1', architecture.ARCH_ARM64, 'ga'),
    (os.path.join(_CERTS_PATH, '8.1', '279.pem'), '8.1', architecture.ARCH_PPC64LE, 'ga'),
    (os.path.join(_CERTS_PATH, '8.2', '479.pem'), '8.2', architecture.ARCH_X86_64, 'ga'),
    (os.path.join(_CERTS_PATH, '8.5', '486.pem'), '8.5', architecture.ARCH_X86_64, 'beta'),
    (os.path.join(_CERTS_PATH, '8.2', '72.pem'), '8.2', architecture.ARCH_S390X, 'ga'),
    (os.path.join(_CERTS_PATH, '8.5', '433.pem'), '8.5', architecture.ARCH_S390X, 'beta'),
])
def test_get_product_certificate_path(monkeypatch, adjust_cwd, result, dst_ver, arch, prod_type):
    envars = {'LEAPP_DEVEL_TARGET_PRODUCT_TYPE': prod_type}
    curr_actor_mocked = CurrentActorMocked(dst_ver=dst_ver, arch=arch, envars=envars)
    monkeypatch.setattr(userspacegen.api, 'current_actor', curr_actor_mocked)
    assert userspacegen._get_product_certificate_path() in result


@suppress_deprecation(models.RequiredTargetUserspacePackages)
def _gen_packages_msgs():
    _cfiles = [
        models.CopyFile(src='/path/src', dst='/path/dst'),
        models.CopyFile(src='/path/foo', dst='/path/bar'),
    ]
    return [
        models.RequiredTargetUserspacePackages(),
        models.RequiredTargetUserspacePackages(packages=['pkgA']),
        models.RequiredTargetUserspacePackages(packages=['pkgB', 'pkgsC']),
        models.RequiredTargetUserspacePackages(packages=['pkgD']),
        models.TargetUserSpacePreupgradeTasks(),
        models.TargetUserSpacePreupgradeTasks(install_rpms=['pkgA']),
        models.TargetUserSpacePreupgradeTasks(install_rpms=['pkgB', 'pkgsC']),
        models.TargetUserSpacePreupgradeTasks(install_rpms=['pkgD', 'pkgE'], copy_files=[_cfiles[0]]),
        models.TargetUserSpacePreupgradeTasks(copy_files=_cfiles),
    ]


_PACKAGES_MSGS = _gen_packages_msgs()
_RHSMINFO_MSG = models.RHSMInfo(attached_skus=['testing-sku'])
_RHUIINFO_MSG = models.RHUIInfo(provider='aws')
_XFS_MSG = models.XFSPresence()
_STORAGEINFO_MSG = models.StorageInfo()
_CTRF_MSGS = [
    models.CustomTargetRepositoryFile(file='rfileA'),
    models.CustomTargetRepositoryFile(file='rfileB'),
]
_SAEE = StopActorExecutionError
_SAE = StopActorExecution


class MockedConsume(object):
    def __init__(self, *args):
        self._msgs = []
        for arg in args:
            if not arg:
                continue
            if isinstance(arg, list):
                self._msgs.extend(arg)
            else:
                self._msgs.append(arg)

    def __call__(self, model):
        return iter([msg for msg in self._msgs if isinstance(msg, model)])


testInData = namedtuple(
    'TestInData', ['pkg_msgs', 'rhsm_info', 'rhui_info', 'xfs', 'storage', 'custom_repofiles']
)


# NOTE: tests cover know new, deprecated, and both ways how to require packages
# that should be installed to create the target userspace. Cases which could be
# removed completely after the drop of the deprecated functionality, are marked
# with the `# dep` str.
@pytest.mark.parametrize('raised,no_rhsm,testdata', [
    # valid cases with RHSM
    (None, '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),
    (None, '0', testInData(_PACKAGES_MSGS[:4], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),   # dep
    (None, '0', testInData(_PACKAGES_MSGS[4:8], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),  # dep
    (None, '0', testInData(_PACKAGES_MSGS[0], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),
    (None, '0', testInData(_PACKAGES_MSGS[4], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),    # dep
    (None, '0', testInData([], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),
    (None, '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, None, _STORAGEINFO_MSG, None)),
    (None, '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, _CTRF_MSGS)),
    (None, '0', testInData(_PACKAGES_MSGS[0], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, _CTRF_MSGS)),
    (None, '0', testInData(_PACKAGES_MSGS[4], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, _CTRF_MSGS)),  # dep
    (None, '0', testInData([], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, _CTRF_MSGS)),
    (None, '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, None, _STORAGEINFO_MSG, _CTRF_MSGS)),

    # valid cases without RHSM (== skip_rhsm)
    (None, '1', testInData(_PACKAGES_MSGS, None, _RHUIINFO_MSG, _XFS_MSG, _STORAGEINFO_MSG, None)),
    (None, '1', testInData(_PACKAGES_MSGS[:4], None, _RHUIINFO_MSG, _XFS_MSG, _STORAGEINFO_MSG, None)),   # dep
    (None, '1', testInData(_PACKAGES_MSGS[4:8], None, _RHUIINFO_MSG, _XFS_MSG, _STORAGEINFO_MSG, None)),  # dep
    (None, '1', testInData(_PACKAGES_MSGS, None, _RHUIINFO_MSG, None, _STORAGEINFO_MSG, None)),
    (None, '1', testInData([], None, _RHUIINFO_MSG, _XFS_MSG, _STORAGEINFO_MSG, None)),
    (None, '1', testInData([], None, _RHUIINFO_MSG, None, _STORAGEINFO_MSG, None)),
    (None, '1', testInData(_PACKAGES_MSGS, None, _RHUIINFO_MSG, _XFS_MSG, _STORAGEINFO_MSG, _CTRF_MSGS)),
    (None, '1', testInData(_PACKAGES_MSGS, None, _RHUIINFO_MSG, None, _STORAGEINFO_MSG, _CTRF_MSGS)),
    (None, '1', testInData([], None, _RHUIINFO_MSG, _XFS_MSG, _STORAGEINFO_MSG, _CTRF_MSGS)),
    (None, '1', testInData([], None, _RHUIINFO_MSG, None, _STORAGEINFO_MSG, _CTRF_MSGS)),

    # no-rhsm but RHSMInfo defined (should be _RHSMINFO_MSG)
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS[0], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG,
                                             None)),
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS[4], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG,
                                             None)),  # dep
    ((_SAEE, 'RHSM is not'), '1', testInData([], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, None, _STORAGEINFO_MSG, None)),
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG,
                                             _CTRF_MSGS)),
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS[0], _RHSMINFO_MSG, None, _XFS_MSG,
                                             _STORAGEINFO_MSG, _CTRF_MSGS)),
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS[4], _RHSMINFO_MSG, None, _XFS_MSG,
                                             _STORAGEINFO_MSG, _CTRF_MSGS)),  # dep
    ((_SAEE, 'RHSM is not'), '1', testInData([], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, _CTRF_MSGS)),
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, None, _STORAGEINFO_MSG, _CTRF_MSGS)),

    # missing RHSMInfo but it should exist
    # NOTE: should be this Error?!
    ((_SAE, 'RHSM information'), '0', testInData(_PACKAGES_MSGS, None, None, _XFS_MSG, _STORAGEINFO_MSG, None)),
    ((_SAE, 'RHSM information'), '0', testInData(_PACKAGES_MSGS, None, None, None, _STORAGEINFO_MSG, None)),
    ((_SAE, 'RHSM information'), '0', testInData([], None, None, _XFS_MSG, _STORAGEINFO_MSG, None)),
    ((_SAE, 'RHSM information'), '0', testInData([], None, None, None, _STORAGEINFO_MSG, None)),

    # in the end, error when StorageInfo is missing
    ((_SAEE, 'No storage'), '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, _XFS_MSG, None, None)),
    ((_SAEE, 'No storage'), '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, None, None, None)),
    ((_SAEE, 'No storage'), '0', testInData([], _RHSMINFO_MSG, None, _XFS_MSG, None, None)),
    ((_SAEE, 'No storage'), '0', testInData([], _RHSMINFO_MSG, None, None, None, None)),
    ((_SAEE, 'No storage'), '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, _XFS_MSG, None, _CTRF_MSGS)),
    ((_SAEE, 'No storage'), '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, None, None, _CTRF_MSGS)),
    ((_SAEE, 'No storage'), '0', testInData([], _RHSMINFO_MSG, None, _XFS_MSG, None, _CTRF_MSGS)),
    ((_SAEE, 'No storage'), '0', testInData([], _RHSMINFO_MSG, None, None, None, _CTRF_MSGS)),
])
def test_consume_data(monkeypatch, raised, no_rhsm, testdata):
    # do not write never into testdata inside the test !!
    xfs = testdata.xfs
    custom_repofiles = testdata.custom_repofiles
    _exp_pkgs = {'dnf', 'dnf-command(config-manager)'}
    _exp_files = []

    def _get_pkgs(msg):
        if isinstance(msg, models.TargetUserSpacePreupgradeTasks):
            return msg.install_rpms
        return msg.packages

    def _get_files(msg):
        if isinstance(msg, models.TargetUserSpacePreupgradeTasks):
            return msg.copy_files
        return []

    def _cfiles2set(cfiles):
        return {(i.src, i.dst) for i in cfiles}

    if isinstance(testdata.pkg_msgs, list):
        for msg in testdata.pkg_msgs:
            _exp_pkgs.update(_get_pkgs(msg))
            _exp_files += _get_files(msg)
    else:
        _exp_pkgs.update(_get_pkgs(testdata.pkg_msgs))
        _exp_files += _get_files(testdata.pkg_msgs)
    mocked_consume = MockedConsume(testdata.pkg_msgs,
                                   testdata.rhsm_info,
                                   testdata.rhui_info,
                                   xfs,
                                   testdata.storage,
                                   custom_repofiles)

    monkeypatch.setattr(userspacegen.api, 'consume', mocked_consume)
    monkeypatch.setattr(userspacegen.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked(envars={'LEAPP_NO_RHSM': no_rhsm}))
    if not xfs:
        xfs = models.XFSPresence()
    if not custom_repofiles:
        custom_repofiles = []
    if not raised:
        result = userspacegen._InputData()
        assert result.packages == _exp_pkgs
        assert _cfiles2set(result.files) == _cfiles2set(_exp_files)
        assert result.rhsm_info == testdata.rhsm_info
        assert result.rhui_info == testdata.rhui_info
        assert result.xfs_info == xfs
        assert result.storage_info == testdata.storage
        assert result.custom_repofiles == custom_repofiles
        assert not userspacegen.api.current_logger.warnmsg
        assert not userspacegen.api.current_logger.errmsg
    else:
        with pytest.raises(raised[0]) as err:
            userspacegen._InputData()
        if isinstance(err.value, StopActorExecutionError):
            assert raised[1] in err.value.message
        else:
            assert userspacegen.api.current_logger.warnmsg
            assert any([raised[1] in x for x in userspacegen.api.current_logger.warnmsg])


@pytest.mark.skip(reason="Currently not implemented in the actor. It's TODO.")
def test_gather_target_repositories(monkeypatch):
    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked())
    # The available RHSM repos
    monkeypatch.setattr(rhsm, 'get_available_repo_ids', lambda x: ['repoidX', 'repoidY', 'repoidZ'])
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: False)
    # The required RHEL repos based on the repo mapping and PES data + custom repos required by third party actors
    monkeypatch.setattr(userspacegen.api, 'consume', lambda x: iter([models.TargetRepositories(
        rhel_repos=[models.RHELTargetRepository(repoid='repoidX'),
                    models.RHELTargetRepository(repoid='repoidY')],
        custom_repos=[models.CustomTargetRepository(repoid='repoidCustom')])]))

    target_repoids = userspacegen.gather_target_repositories(None, None)

    assert target_repoids == ['repoidX', 'repoidY', 'repoidCustom']


def test_gather_target_repositories_none_available(monkeypatch):

    mocked_produce = produce_mocked()
    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(userspacegen.api.current_actor(), 'produce', mocked_produce)
    monkeypatch.setattr(rhsm, 'get_available_repo_ids', lambda x: [])
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: False)
    with pytest.raises(StopActorExecution):
        userspacegen.gather_target_repositories(None, None)
        assert mocked_produce.called
        reports = [m.report for m in mocked_produce.model_instances if isinstance(m, reporting.Report)]
        inhibitors = [m for m in reports if 'INHIBITOR' in m.get('flags', ())]
        assert len(inhibitors) == 1
        assert inhibitors[0].get('title', '') == 'Cannot find required basic RHEL target repositories.'


def test_gather_target_repositories_rhui(monkeypatch):

    indata = testInData(
        _PACKAGES_MSGS, _RHSMINFO_MSG, _RHUIINFO_MSG, _XFS_MSG, _STORAGEINFO_MSG, None
    )

    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(userspacegen, '_get_all_available_repoids', lambda x: [])
    monkeypatch.setattr(
        userspacegen, '_get_rh_available_repoids', lambda x, y: ['rhui-1', 'rhui-2', 'rhui-3']
    )
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: True)
    monkeypatch.setattr(
        userspacegen.api, 'consume', lambda x: iter(
            [models.TargetRepositories(
                rhel_repos=[
                    models.RHELTargetRepository(repoid='rhui-1'),
                    models.RHELTargetRepository(repoid='rhui-2')
                ]
            )
            ])
    )
    target_repoids = userspacegen.gather_target_repositories(None, indata)
    assert target_repoids == set(['rhui-1', 'rhui-2'])


def test_gather_target_repositories_baseos_appstream_not_available(monkeypatch):
    # If the repos that Leapp identifies as required for the upgrade (based on the repo mapping and PES data) are not
    # available, an exception shall be raised

    indata = testInData(
        _PACKAGES_MSGS, _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None
    )
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: False)

    mocked_produce = produce_mocked()
    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(userspacegen.api.current_actor(), 'produce', mocked_produce)
    # The available RHSM repos
    monkeypatch.setattr(rhsm, 'get_available_repo_ids', lambda x: ['repoidA', 'repoidB', 'repoidC'])
    # The required RHEL repos based on the repo mapping and PES data + custom repos required by third party actors
    monkeypatch.setattr(userspacegen.api, 'consume', lambda x: iter([models.TargetRepositories(
        rhel_repos=[models.RHELTargetRepository(repoid='repoidX'),
                    models.RHELTargetRepository(repoid='repoidY')],
        custom_repos=[models.CustomTargetRepository(repoid='repoidCustom')])]))

    with pytest.raises(StopActorExecution):
        userspacegen.gather_target_repositories(None, indata)
    assert mocked_produce.called
    reports = [m.report for m in mocked_produce.model_instances if isinstance(m, reporting.Report)]
    inhibitors = [m for m in reports if 'inhibitor' in m.get('groups', ())]
    assert len(inhibitors) == 1
    assert inhibitors[0].get('title', '') == 'Cannot find required basic RHEL target repositories.'
    # Now test the case when either of AppStream and BaseOs is not available, upgrade should be inhibited
    mocked_produce = produce_mocked()
    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(userspacegen.api.current_actor(), 'produce', mocked_produce)
    monkeypatch.setattr(rhsm, 'get_available_repo_ids', lambda x: ['repoidA', 'repoidB', 'repoidC-appstream'])
    monkeypatch.setattr(userspacegen.api, 'consume', lambda x: iter([models.TargetRepositories(
        rhel_repos=[models.RHELTargetRepository(repoid='repoidC-appstream'),
                    models.RHELTargetRepository(repoid='repoidA')],
        custom_repos=[models.CustomTargetRepository(repoid='repoidCustom')])]))
    with pytest.raises(StopActorExecution):
        userspacegen.gather_target_repositories(None, indata)
    reports = [m.report for m in mocked_produce.model_instances if isinstance(m, reporting.Report)]
    inhibitors = [m for m in reports if 'inhibitor' in m.get('groups', ())]
    assert len(inhibitors) == 1
    assert inhibitors[0].get('title', '') == 'Cannot find required basic RHEL target repositories.'
    mocked_produce = produce_mocked()
    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(userspacegen.api.current_actor(), 'produce', mocked_produce)
    monkeypatch.setattr(rhsm, 'get_available_repo_ids', lambda x: ['repoidA', 'repoidB', 'repoidC-baseos'])
    monkeypatch.setattr(userspacegen.api, 'consume', lambda x: iter([models.TargetRepositories(
        rhel_repos=[models.RHELTargetRepository(repoid='repoidC-baseos'),
                    models.RHELTargetRepository(repoid='repoidA')],
        custom_repos=[models.CustomTargetRepository(repoid='repoidCustom')])]))
    with pytest.raises(StopActorExecution):
        userspacegen.gather_target_repositories(None, indata)
    reports = [m.report for m in mocked_produce.model_instances if isinstance(m, reporting.Report)]
    inhibitors = [m for m in reports if 'inhibitor' in m.get('groups', ())]
    assert len(inhibitors) == 1
    assert inhibitors[0].get('title', '') == 'Cannot find required basic RHEL target repositories.'


def mocked_consume_data():
    packages = {'dnf', 'dnf-command(config-manager)', 'pkgA', 'pkgB'}
    rhsm_info = _RHSMINFO_MSG
    rhui_info = _RHUIINFO_MSG
    xfs_info = models.XFSPresence()
    storage_info = models.StorageInfo()
    custom_repofiles = []
    files = set()
    fields = [
        'packages',
        'rhsm_info',
        'rhui_info',
        'xfs_info',
        'storage_info',
        'custom_repofiles',
        'files'
    ]

    return namedtuple('TestInData', fields)(
                packages,
                rhsm_info,
                rhui_info,
                xfs_info,
                storage_info,
                custom_repofiles,
                files,
    )


# TODO: come up with additional tests for the main function
def test_perform_ok(monkeypatch):
    repoids = ['repoidX', 'repoidY']
    monkeypatch.setattr(userspacegen, '_InputData', mocked_consume_data)
    monkeypatch.setattr(userspacegen, '_get_product_certificate_path', lambda: _DEFAULT_CERT_PATH)
    monkeypatch.setattr(overlaygen, 'create_source_overlay', MockedMountingBase)
    monkeypatch.setattr(userspacegen, '_gather_target_repositories', lambda *x: repoids)
    monkeypatch.setattr(userspacegen, '_create_target_userspace', lambda *x: None)
    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(userspacegen.api, 'produce', produce_mocked())
    monkeypatch.setattr(repofileutils, 'get_repodirs', lambda: ['/etc/yum.repos.d'])
    userspacegen.perform()
    msg_target_repos = models.UsedTargetRepositories(
        repos=[models.UsedTargetRepository(repoid=repo) for repo in repoids])
    assert userspacegen.api.produce.called == 3
    assert isinstance(userspacegen.api.produce.model_instances[0], models.TMPTargetRepositoriesFacts)
    assert userspacegen.api.produce.model_instances[1] == msg_target_repos
    # this one is full of constants, so it's safe to check just the instance
    assert isinstance(userspacegen.api.produce.model_instances[2], models.TargetUserSpaceInfo)
