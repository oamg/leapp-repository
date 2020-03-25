from collections import namedtuple
import os

import pytest

from leapp.exceptions import StopActorExecutionError, StopActorExecution
from leapp.libraries.actor import userspacegen
from leapp.libraries.common import overlaygen, rhsm
from leapp.libraries.common import testutils
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp import models


_CERTS_PATH = os.path.join('../../files', userspacegen.PROD_CERTS_FOLDER)
_DEFAULT_CERT_PATH = os.path.join(_CERTS_PATH, '8.1', '479.pem')


class CurrentActorMocked(object):
    def __init__(self, kernel='3.10.0-957.43.1.el7.x86_64', release_id='rhel',
                 src_ver='7.6', dst_ver='8.1', arch=architecture.ARCH_X86_64,
                 envars=None):

        if envars:
            envarsList = [models.EnvVar(name=key, value=value) for key, value in envars.items()]
        else:
            envarsList = []

        version = namedtuple('Version', ['source', 'target'])(src_ver, dst_ver)
        os_release = namedtuple('OS_release', ['release_id', 'version_id'])(release_id, src_ver)
        args = (version, kernel, os_release, arch, envarsList)
        conf_fields = ['version', 'kernel', 'os_release', 'architecture', 'leapp_env_vars']
        self.configuration = namedtuple('configuration', conf_fields)(*args)
        self._common_folder = '../../files'

    def __call__(self):
        return self

    def get_common_folder_path(self, folder):
        return os.path.join(self._common_folder, folder)


class MockedMountingBase(object):
    def __init__(self, **dummy_kwargs):
        self.called_copytree_from = []

    def copytree_from(self, src, dst):
        self.called_copytree_from.append((src, dst))

    def __call__(self, **dummy_kwarg):
        yield self

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
    (os.path.join(_CERTS_PATH, '8.2', '230.pem'), '8.2', architecture.ARCH_X86_64, 'htb'),
    (os.path.join(_CERTS_PATH, '8.2', '486.pem'), '8.2', architecture.ARCH_X86_64, 'beta'),
    (os.path.join(_CERTS_PATH, '8.2', '72.pem'), '8.2', architecture.ARCH_S390X, 'ga'),
    (os.path.join(_CERTS_PATH, '8.2', '232.pem'), '8.2', architecture.ARCH_S390X, 'htb'),
    (os.path.join(_CERTS_PATH, '8.2', '433.pem'), '8.2', architecture.ARCH_S390X, 'beta'),
])
def test_get_product_certificate_path(monkeypatch, result, dst_ver, arch, prod_type):
    envars = {'LEAPP_DEVEL_TARGET_PRODUCT_TYPE': prod_type}
    curr_actor_mocked = CurrentActorMocked(dst_ver=dst_ver, arch=arch, envars=envars)
    monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
    assert userspacegen._get_product_certificate_path() == result


class mocked_logger(object):
    def __init__(self):
        self.errmsg = []
        self.warnmsg = []
        self.debugmsg = []

    def error(self, msg):
        self.errmsg.append(msg)

    def warn(self, msg):
        self.warnmsg.append(msg)

    def debug(self, msg):
        self.debugmsg.append(msg)

    def __call__(self):
        return self


_PACKAGES_MSGS = [
    models.RequiredTargetUserspacePackages(),
    models.RequiredTargetUserspacePackages(packages=['pkgA']),
    models.RequiredTargetUserspacePackages(packages=['pkgB', 'pkgsC']),
    models.RequiredTargetUserspacePackages(packages=['pkgD']),
]
_RHSMINFO_MSG = models.RHSMInfo(attached_skus=['testing-sku'])
_XFS_MSG = models.XFSPresence()
_STORAGEINFO_MSG = models.StorageInfo()


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


# FIXME: the results should be probably different with supported disconnected
# systems (see rhsm)
# undefined: (????, _PACKAGES_MSGS, None, _XFS_MSG, None),
@pytest.mark.parametrize('raised,pkg_msgs,rhsm_info,xfs,storage', [
    (None, _PACKAGES_MSGS, _RHSMINFO_MSG, _XFS_MSG, _STORAGEINFO_MSG),
    (None, _PACKAGES_MSGS[0], _RHSMINFO_MSG, _XFS_MSG, _STORAGEINFO_MSG),
    (None, [], _RHSMINFO_MSG, _XFS_MSG, _STORAGEINFO_MSG),
    (None, _PACKAGES_MSGS, _RHSMINFO_MSG, None, _STORAGEINFO_MSG),
    ((StopActorExecution, 'RHSM information'), _PACKAGES_MSGS, None, _XFS_MSG, _STORAGEINFO_MSG),
    ((StopActorExecution, 'RHSM information'), _PACKAGES_MSGS, None, None, _STORAGEINFO_MSG),
    ((StopActorExecution, 'RHSM information'), [], None, _XFS_MSG, _STORAGEINFO_MSG),
    ((StopActorExecution, 'RHSM information'), [], None, None, _STORAGEINFO_MSG),
    ((StopActorExecutionError, 'No storage'), _PACKAGES_MSGS, _RHSMINFO_MSG, _XFS_MSG, None),
    ((StopActorExecutionError, 'No storage'), _PACKAGES_MSGS, _RHSMINFO_MSG, None, None),
    ((StopActorExecutionError, 'No storage'), [], _RHSMINFO_MSG, _XFS_MSG, None),
    ((StopActorExecutionError, 'No storage'), [], _RHSMINFO_MSG, None, None),
])
def test_consume_data(monkeypatch, raised, pkg_msgs, rhsm_info, xfs, storage):
    _exp_pkgs = {'dnf'}
    if isinstance(pkg_msgs, list):
        for msg in pkg_msgs:
            _exp_pkgs.update(msg.packages)
    else:
        _exp_pkgs.update(pkg_msgs.packages)
    mocked_consume = MockedConsume(pkg_msgs, rhsm_info, xfs, storage)
    monkeypatch.setattr(api, 'consume', mocked_consume)
    monkeypatch.setattr(api, 'current_logger', mocked_logger())
    monkeypatch.setenv('LEAPP_DEVEL_SKIP_RHSM', '0')
    if not xfs:
        xfs = models.XFSPresence()
    if not raised:
        assert userspacegen._consume_data() == (_exp_pkgs, rhsm_info, xfs, storage)
        assert not api.current_logger.warnmsg
        assert not api.current_logger.errmsg
    else:
        with pytest.raises(raised[0]) as err:
            userspacegen._consume_data()
        if isinstance(err.value, StopActorExecutionError):
            assert raised[1] in err.value.message
        else:
            assert api.current_logger.warnmsg
            assert any([raised[1] in x for x in api.current_logger.warnmsg])


@pytest.mark.skip(reason="Currently not implemented in the actor. It's TODO.")
def test_gather_target_repositories(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    # The available RHSM repos
    monkeypatch.setattr(rhsm, 'get_available_repo_ids', lambda x: ['repoidX', 'repoidY', 'repoidZ'])
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: False)
    # The required RHEL repos based on the repo mapping and PES data + custom repos required by third party actors
    monkeypatch.setattr(api, 'consume', lambda x: iter([models.TargetRepositories(
        rhel_repos=[models.RHELTargetRepository(repoid='repoidX'),
                    models.RHELTargetRepository(repoid='repoidY')],
        custom_repos=[models.CustomTargetRepository(repoid='repoidCustom')])]))

    target_repoids = userspacegen.gather_target_repositories(None)

    assert target_repoids == ['repoidX', 'repoidY', 'repoidCustom']


def test_gather_target_repositories_none_available(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(rhsm, 'get_available_repo_ids', lambda x: [])
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: False)
    with pytest.raises(StopActorExecutionError) as err:
        userspacegen.gather_target_repositories(None)
    assert "Cannot find required basic RHEL 8 repositories" in str(err)


@pytest.mark.skip(reason="Currently not implemented in the actor. It's TODO.")
def test_gather_target_repositories_required_not_available(monkeypatch):
    # If the repos that Leapp identifies as required for the upgrade (based on the repo mapping and PES data) are not
    # available, an exception shall be raised

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked)
    # The available RHSM repos
    monkeypatch.setattr(rhsm, 'get_available_repo_ids', lambda x: ['repoidA', 'repoidB', 'repoidC'])
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: False)
    # The required RHEL repos based on the repo mapping and PES data + custom repos required by third party actors
    monkeypatch.setattr(api, 'consume', lambda x: iter([models.TargetRepositories(
        rhel_repos=[models.RHELTargetRepository(repoid='repoidX'),
                    models.RHELTargetRepository(repoid='repoidY')],
        custom_repos=[models.CustomTargetRepository(repoid='repoidCustom')])]))

    with pytest.raises(StopActorExecutionError) as err:
        userspacegen.gather_target_repositories(None)
    assert "Cannot find required basic RHEL 8 repositories" in str(err)


def mocked_consume_data():
    packages = {'dnf', 'pkgA', 'pkgB'}
    rhsm_info = _RHSMINFO_MSG
    xfs_info = models.XFSPresence()
    storage_info = models.StorageInfo()
    return packages, rhsm_info, xfs_info, storage_info


# TODO: come up with additional tests for the main function
def test_perform_ok(monkeypatch):
    repoids = ['repoidX', 'repoidY']
    monkeypatch.setattr(userspacegen, '_consume_data', mocked_consume_data)
    monkeypatch.setattr(userspacegen, '_get_product_certificate_path', lambda: _DEFAULT_CERT_PATH)
    monkeypatch.setattr(overlaygen, 'create_source_overlay', MockedMountingBase)
    monkeypatch.setattr(userspacegen, '_gather_target_repositories', lambda *x: repoids)
    monkeypatch.setattr(userspacegen, '_create_target_userspace', lambda *x: None)
    monkeypatch.setattr(api, 'produce', testutils.produce_mocked())
    userspacegen.perform()
    msg_target_repos = models.UsedTargetRepositories(
            repos=[models.UsedTargetRepository(repoid=repo) for repo in repoids])
    assert api.produce.called == 2
    assert api.produce.model_instances[0] == msg_target_repos
    # this one is full of contants, so it's safe to check just the instance
    assert isinstance(api.produce.model_instances[1], models.TargetUserSpaceInfo)
