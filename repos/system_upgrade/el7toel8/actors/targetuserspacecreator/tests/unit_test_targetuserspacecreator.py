import os
from collections import namedtuple

import pytest

from leapp import models
from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp.libraries.actor import userspacegen
from leapp.libraries.common import overlaygen, repofileutils, rhsm
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked

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
    (os.path.join(_CERTS_PATH, '8.3', '230.pem'), '8.3', architecture.ARCH_X86_64, 'htb'),
    (os.path.join(_CERTS_PATH, '8.3', '486.pem'), '8.3', architecture.ARCH_X86_64, 'beta'),
    (os.path.join(_CERTS_PATH, '8.2', '72.pem'), '8.2', architecture.ARCH_S390X, 'ga'),
    (os.path.join(_CERTS_PATH, '8.3', '232.pem'), '8.3', architecture.ARCH_S390X, 'htb'),
    (os.path.join(_CERTS_PATH, '8.3', '433.pem'), '8.3', architecture.ARCH_S390X, 'beta'),
])
def test_get_product_certificate_path(monkeypatch, adjust_cwd, result, dst_ver, arch, prod_type):
    envars = {'LEAPP_DEVEL_TARGET_PRODUCT_TYPE': prod_type}
    curr_actor_mocked = CurrentActorMocked(dst_ver=dst_ver, arch=arch, envars=envars)
    monkeypatch.setattr(userspacegen.api, 'current_actor', curr_actor_mocked)
    assert userspacegen._get_product_certificate_path() in result


_PACKAGES_MSGS = [
    models.RequiredTargetUserspacePackages(),
    models.RequiredTargetUserspacePackages(packages=['pkgA']),
    models.RequiredTargetUserspacePackages(packages=['pkgB', 'pkgsC']),
    models.RequiredTargetUserspacePackages(packages=['pkgD']),
]
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


@pytest.mark.parametrize('raised,no_rhsm,testdata', [
    # valid cases with RHSM
    (None, '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),
    (None, '0', testInData(_PACKAGES_MSGS[0], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),
    (None, '0', testInData([], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),
    (None, '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, None, _STORAGEINFO_MSG, None)),
    (None, '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, _CTRF_MSGS)),
    (None, '0', testInData(_PACKAGES_MSGS[0], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, _CTRF_MSGS)),
    (None, '0', testInData([], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, _CTRF_MSGS)),
    (None, '0', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, None, _STORAGEINFO_MSG, _CTRF_MSGS)),

    # valid cases without RHSM (== skip_rhsm)
    (None, '1', testInData(_PACKAGES_MSGS, None, _RHUIINFO_MSG, _XFS_MSG, _STORAGEINFO_MSG, None)),
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
    ((_SAEE, 'RHSM is not'), '1', testInData([], _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG, None)),
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, None, _STORAGEINFO_MSG, None)),
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS, _RHSMINFO_MSG, None, _XFS_MSG, _STORAGEINFO_MSG,
                                             _CTRF_MSGS)),
    ((_SAEE, 'RHSM is not'), '1', testInData(_PACKAGES_MSGS[0], _RHSMINFO_MSG, None, _XFS_MSG,
                                             _STORAGEINFO_MSG, _CTRF_MSGS)),
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
    _exp_pkgs = {'dnf'}
    if isinstance(testdata.pkg_msgs, list):
        for msg in testdata.pkg_msgs:
            _exp_pkgs.update(msg.packages)
    else:
        _exp_pkgs.update(testdata.pkg_msgs.packages)
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

    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(rhsm, 'get_available_repo_ids', lambda x: [])
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: False)
    with pytest.raises(StopActorExecutionError) as err:
        userspacegen.gather_target_repositories(None, None)
    assert "Cannot find required basic RHEL 8 repositories" in str(err)


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


@pytest.mark.skip(reason="Currently not implemented in the actor. It's TODO.")
def test_gather_target_repositories_required_not_available(monkeypatch):
    # If the repos that Leapp identifies as required for the upgrade (based on the repo mapping and PES data) are not
    # available, an exception shall be raised

    monkeypatch.setattr(userspacegen.api, 'current_actor', CurrentActorMocked())
    # The available RHSM repos
    monkeypatch.setattr(rhsm, 'get_available_repo_ids', lambda x: ['repoidA', 'repoidB', 'repoidC'])
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: False)
    # The required RHEL repos based on the repo mapping and PES data + custom repos required by third party actors
    monkeypatch.setattr(userspacegen.api, 'consume', lambda x: iter([models.TargetRepositories(
        rhel_repos=[models.RHELTargetRepository(repoid='repoidX'),
                    models.RHELTargetRepository(repoid='repoidY')],
        custom_repos=[models.CustomTargetRepository(repoid='repoidCustom')])]))

    with pytest.raises(StopActorExecutionError) as err:
        userspacegen.gather_target_repositories(None)
    assert "Cannot find required basic RHEL 8 repositories" in str(err)


def mocked_consume_data():
    packages = {'dnf', 'pkgA', 'pkgB'}
    rhsm_info = _RHSMINFO_MSG
    rhui_info = _RHUIINFO_MSG
    xfs_info = models.XFSPresence()
    storage_info = models.StorageInfo()
    custom_repofiles = []
    fields = ['packages', 'rhsm_info', 'rhui_info', 'xfs_info', 'storage_info', 'custom_repofiles']

    return namedtuple('TestInData', fields)(
                packages, rhsm_info, rhui_info, xfs_info, storage_info, custom_repofiles
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
    # this one is full of contants, so it's safe to check just the instance
    assert isinstance(userspacegen.api.produce.model_instances[2], models.TargetUserSpaceInfo)
