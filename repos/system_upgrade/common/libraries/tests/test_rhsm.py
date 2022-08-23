import os
from collections import namedtuple

import pytest

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import repofileutils, rhsm
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import RepositoryData, RepositoryFile
from leapp.utils.report import is_inhibitor

Repository = namedtuple('Repository', ['repoid', 'file'])
LIST_SEPARATOR = '\n    - '

# External commands called by the RHSM library
CMD_RHSM_LIST_CONSUMED = ('subscription-manager', 'list', '--consumed')
CMD_RHSM_STATUS = ('subscription-manager', 'status')
CMD_RHSM_RELEASE = ('subscription-manager', 'release')
CMD_RHSM_LIST_ENABLED_REPOS = ('subscription-manager', 'repos', '--list-enabled')

RHSM_STATUS_OUTPUT_NOSCA = '''
+-------------------------------------------+
   System Status Details
+-------------------------------------------+
Overall Status: Current

System Purpose Status: Not Specified
'''

RHSM_STATUS_OUTPUT_SCA = '''
+-------------------------------------------+
   System Status Details
+-------------------------------------------+
Overall Status: Current

System Purpose Status: Matched

Content Access Mode is set to Simple Content Access
'''

# Used to simulate realistic output of RHSM, therefore carries more information than `Repository` namedtuple
RHSMRepositoryEntry = namedtuple('RHSMRepositoryEntry', ('id', 'name', 'url', 'enabled'))  # For clarity purposes
RHSM_ENABLED_REPOS = [
    RHSMRepositoryEntry(
        id='rhel-8-for-x86_64-appstream-rpms',
        name='Appstream',
        url='some_url',
        enabled='1'),
    RHSMRepositoryEntry(
        id='satellite-tools-6.6-for-rhel-8-x86_64-rpms',
        name='Satellite',
        url='some_url',
        enabled='1'),
    RHSMRepositoryEntry(
        id='rhel-8-for-x86_64-baseos-rpms',
        name='Base',
        url='some_url',
        enabled='1')
]


class IsolatedActionsMocked(object):
    def __init__(self, call_stdout=None, raise_err=False):
        self.commands_called = []
        self.call_return = {'stdout': call_stdout, 'stderr': None}
        self.raise_err = raise_err

        # A map from called commands to their mocked output
        self.mocked_command_call_outputs = dict()

    def call(self, cmd, *args, **dummy_kwargs):
        self.commands_called.append(cmd)
        if self.raise_err:
            raise_call_error(cmd)

        return self.mocked_command_call_outputs.get(
            tuple(cmd),  # Cast to tuple, as list is not hashable
            self.call_return)

    def add_mocked_command_call_with_stdout(self, cmd, stdout):
        # We cast `cmd` from list to tuple, as a list cannot be hashed
        self.mocked_command_call_outputs[tuple(cmd)] = {
            'stdout': stdout,
            'stderr': None}

    def full_path(self, path):
        return path


@pytest.fixture
def actor_mocked(monkeypatch):
    """
    Fixture providing a mocked actor that was already used to monkeypatch api.current_actor.

    Introduced to reduce repetition inside tests.
    """
    actor = CurrentActorMocked()
    monkeypatch.setattr(api, 'current_actor', actor)
    return actor


@pytest.fixture
def context_mocked():
    return IsolatedActionsMocked()


def raise_call_error(args=None, exit_code=1):
    raise CalledProcessError(
        message='Command {0} failed with exit code {1}.'.format(str(args), exit_code),
        command=args,
        result={'signal': None, 'exit_code': exit_code, 'pid': 0, 'stdout': 'fake out', 'stderr': 'fake err'}
    )


def _gen_repo(repoid):
    return RepositoryData(repoid=repoid, name='name {}'.format(repoid))


def _gen_repofile(rfile, data=None):
    if data is None:
        data = [_gen_repo("{}-{}".format(rfile.split("/")[-1], i)) for i in range(3)]
    return RepositoryFile(file=rfile, data=data)


@pytest.mark.parametrize('other_repofiles', [
    [],
    [_gen_repofile("foo")],
    [_gen_repofile("foo"), _gen_repofile("bar")],
])
@pytest.mark.parametrize('rhsm_repofile', [
    None,
    _gen_repofile(rhsm._DEFAULT_RHSM_REPOFILE, []),
    _gen_repofile(rhsm._DEFAULT_RHSM_REPOFILE, [_gen_repo("rh-0")]),
    _gen_repofile(rhsm._DEFAULT_RHSM_REPOFILE),
])
def test_get_available_repo_ids(monkeypatch, other_repofiles, rhsm_repofile):
    context_mocked = IsolatedActionsMocked()
    repos = other_repofiles[:]
    if rhsm_repofile:
        repos.append(rhsm_repofile)
    rhsm_repos = [repo.repoid for repo in rhsm_repofile.data] if rhsm_repofile else []

    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(rhsm, '_inhibit_on_duplicate_repos', lambda x: None)
    monkeypatch.setattr(repofileutils, 'get_parsed_repofiles', lambda x: repos)

    result = rhsm.get_available_repo_ids(context_mocked)

    rhsm_repos.sort()
    assert context_mocked.commands_called == [['yum', 'clean', 'all']]
    assert result == rhsm_repos
    if result:
        msg = (
            'The following repoids are available through RHSM:{0}{1}'
            .format(LIST_SEPARATOR, LIST_SEPARATOR.join(rhsm_repos))
        )
        assert msg in api.current_logger.infomsg
    else:
        assert 'There are no repos available through RHSM.' in api.current_logger.infomsg


def test_get_available_repo_ids_error():
    context_mocked = IsolatedActionsMocked(raise_err=True)

    with pytest.raises(StopActorExecutionError) as err:
        rhsm.get_available_repo_ids(context_mocked)

    assert 'Unable to use yum' in str(err)


def test_inhibit_on_duplicate_repos(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    repofiles = [
        _gen_repofile("foo", [_gen_repo('repoX'), _gen_repo('repoY')]),
        _gen_repofile("bar", [_gen_repo('repoX')]),
    ]

    rhsm._inhibit_on_duplicate_repos(repofiles)

    dups = ['repoX']
    assert ('The following repoids are defined multiple times:{0}{1}'
            .format(LIST_SEPARATOR, LIST_SEPARATOR.join(dups))) in api.current_logger.warnmsg
    assert reporting.create_report.called == 1
    assert is_inhibitor(reporting.create_report.report_fields)
    assert reporting.create_report.report_fields['title'] == 'A YUM/DNF repository defined multiple times'
    summary = ('The following repositories are defined multiple times:{0}{1}'
               .format(LIST_SEPARATOR, LIST_SEPARATOR.join(dups)))
    assert summary in reporting.create_report.report_fields['summary']


def test_inhibit_on_duplicate_repos_no_dups(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    rhsm._inhibit_on_duplicate_repos([_gen_repofile("foo")])

    assert not api.current_logger.warnmsg
    assert reporting.create_report.called == 0


def test_sku_listing(monkeypatch, actor_mocked, context_mocked):
    """Tests whether the rhsm library can obtain used SKUs correctly."""
    context_mocked.add_mocked_command_call_with_stdout(CMD_RHSM_LIST_CONSUMED, 'SKU: 598339696910')

    attached_skus = rhsm.get_attached_skus(context_mocked)

    assert_fail_description = 'Some calls to subscription-manager were expected.'
    assert context_mocked.commands_called, assert_fail_description

    assert_fail_description = 'RHSM command reported 1 SKU, however {0} were detected.'.format(
        len(attached_skus)
    )
    assert len(attached_skus) == 1, assert_fail_description

    assert_fail_description = 'The parsed SKU is different than the one contained in the mocked RHSM output.'
    assert attached_skus[0] == '598339696910', assert_fail_description


def test_scanrhsminfo_with_skip_rhsm(monkeypatch, context_mocked):
    """Tests whether the scan_rhsm_info respects the LEAPP_NO_RHSM environmental variable."""
    mocked_actor = CurrentActorMocked(envars={'LEAPP_NO_RHSM': '1'})
    monkeypatch.setattr(api, 'current_actor', mocked_actor)

    result = rhsm.scan_rhsm_info(context_mocked)

    assert_fail_description = 'No external shell commands should be executed when RHSM is skipped.'
    assert not context_mocked.commands_called, assert_fail_description

    assert result is None, 'The `scan_rhsm_info` should not provide any output when RHSM is skipped.'


def test_get_release(monkeypatch, actor_mocked, context_mocked):
    """Tests whether the library correctly retrieves release from RHSM."""
    context_mocked.add_mocked_command_call_with_stdout(CMD_RHSM_RELEASE, 'Release: 7.9')

    release = rhsm.get_release(context_mocked)

    assert release, 'No release information detected (but valid release info was provided).'
    assert release == '7.9', 'Detected release is incorrect.'


def test_get_release_with_release_not_set(monkeypatch, actor_mocked, context_mocked):
    """Tests whether the library does not retrieve release information when the release is not set."""
    # Test whether no release is detected correctly too
    context_mocked.add_mocked_command_call_with_stdout(CMD_RHSM_RELEASE, 'Release not set')

    release = rhsm.get_release(context_mocked)

    fail_description = 'The release information was obtained, even if "No release set" was repored by rhsm.'
    assert not release, fail_description


def test_is_manifest_sca_on_nonsca_system(monkeypatch, actor_mocked, context_mocked):
    """Tests whether the library obtains the SCA information correctly from a non-SCA system."""
    context_mocked.add_mocked_command_call_with_stdout(CMD_RHSM_STATUS, RHSM_STATUS_OUTPUT_NOSCA)

    is_sca = rhsm.is_manifest_sca(context_mocked)
    assert not is_sca, 'SCA was detected on a non-SCA system.'


def test_is_manifest_sca_on_sca_system(monkeypatch, actor_mocked, context_mocked):
    """Tests whether the library obtains the SCA information from SCA system correctly."""
    context_mocked.add_mocked_command_call_with_stdout(CMD_RHSM_STATUS, RHSM_STATUS_OUTPUT_SCA)

    is_sca = rhsm.is_manifest_sca(context_mocked)
    assert is_sca, 'Failed to detected SCA on a SCA system.'


def test_get_enabled_repo_ids(monkeypatch, actor_mocked, context_mocked):
    """Tests whether the library retrieves correct information about enabled repositories."""
    # Prepare the (realistic) RHSM output
    rhsm_list_enabled_output = '''
    +----------------------------------------------------------+
       Available Repositories in /etc/yum.repos.d/redhat.repo
    +----------------------------------------------------------+
    '''

    for enabled_repository in RHSM_ENABLED_REPOS:
        rhsm_output_fragment = 'Repo ID: {0}\n'.format(enabled_repository.id)
        rhsm_output_fragment += 'Repo Name: {0}\n'.format(enabled_repository.name)
        rhsm_output_fragment += 'Repo URL: {0}\n'.format(enabled_repository.url)
        rhsm_output_fragment += 'Enabled: {0}\n'.format(enabled_repository.enabled)
        rhsm_output_fragment += '\n'
        rhsm_list_enabled_output += rhsm_output_fragment

    context_mocked.add_mocked_command_call_with_stdout(CMD_RHSM_LIST_ENABLED_REPOS, rhsm_list_enabled_output)

    enabled_repo_ids = rhsm.get_enabled_repo_ids(context_mocked)

    fail_description = 'Failed to detected enabled repositories on the system.'
    assert len(enabled_repo_ids) == 3, fail_description

    fail_description = 'Failed to retrieve repository ID provided in the RHSM output.'
    for enabled_repository in RHSM_ENABLED_REPOS:
        assert enabled_repository.id in enabled_repo_ids, fail_description


def test_get_existing_product_certificates(monkeypatch, actor_mocked, context_mocked):
    """Verifies that the library is able to correctly retrieve existing product certificates."""

    CERT_DIRS_LAYOUT = {
        '/etc/pki/product': ['cert1', 'cert2'],
        '/etc/pki/product-default': ['cert3']
    }

    def mocked_isdir(path):
        if path in CERT_DIRS_LAYOUT:
            return True
        err_message = 'RHSM library should not gather info about additional dirs (attempted to isdir: {0}).'
        raise ValueError(err_message.format(path))

    def mocked_listdir(path):
        if path in CERT_DIRS_LAYOUT:
            return CERT_DIRS_LAYOUT[path]
        err_message = 'RHSM library should not listdir additional dirs (attempted to listdir: {0}).'
        raise ValueError(err_message.format(path))

    def mocked_isfile(path):
        if path in CERT_DIRS_LAYOUT:
            # The certificate directories are not files
            return False

        basename = os.path.basename(path)
        dirname = os.path.dirname(path)
        if dirname in CERT_DIRS_LAYOUT:
            return basename in CERT_DIRS_LAYOUT[dirname]

        err_message = 'RHSM library should not isfile additional paths (attempted to isfile: {0}).'
        raise ValueError(err_message.format(path))

    monkeypatch.setattr(rhsm.os.path, 'isdir', mocked_isdir)
    monkeypatch.setattr(rhsm.os, 'listdir', mocked_listdir)
    monkeypatch.setattr(rhsm.os.path, 'isfile', mocked_isfile)

    existing_product_certificates = rhsm.get_existing_product_certificates(context_mocked)

    fail_description = 'Retrieved different number of certificates than expected.'
    assert len(existing_product_certificates) == 3, fail_description

    fail_description_bad_dir = 'Found certificate in unexpected path: {0}'
    fail_description_bad_cert_file = 'Found certificate file that was not provided by mocked output: {0}'
    for certificate_path in existing_product_certificates:
        dirname = os.path.dirname(certificate_path)
        basename = os.path.basename(certificate_path)
        assert dirname in CERT_DIRS_LAYOUT, fail_description_bad_dir.format(certificate_path)
        assert basename in CERT_DIRS_LAYOUT[dirname], fail_description_bad_cert_file.format(certificate_path)


def test_get_existing_product_certificates_missing_cert_directory(monkeypatch, actor_mocked, context_mocked):
    """Tests whether the library is able to retrieve certificates even if /etc/pki/product is missing."""

    def mocked_isdir(path):
        if path == '/etc/pki/product':
            return False  # Directory is missing
        if path == '/etc/pki/product-default':
            return True

        err_msg = 'Tried to isdir a path that is not a part of the mocked paths. Path: {0}'
        raise ValueError(err_msg.format(path))

    def mocked_isfile(path):
        if path == '/etc/pki/product-default/cert':
            return True

        err_msg = 'Tried to use isfile on a path that is not a part of the mocked paths. Path: {0}'
        raise ValueError(err_msg.format(path))

    def mocked_listdir(path):
        if path == '/etc/pki/product-default':
            return ['cert']

        err_msg = 'Tried to use listdir on a path that is not a part of the mocked paths. Path: {0}'
        raise ValueError(err_msg.format(path))

    monkeypatch.setattr(rhsm.os.path, 'isdir', mocked_isdir)
    monkeypatch.setattr(rhsm.os, 'listdir', mocked_listdir)
    monkeypatch.setattr(rhsm.os.path, 'isfile', mocked_isfile)

    existing_product_certificates = rhsm.get_existing_product_certificates(context_mocked)

    fail_description = 'Library identified more certificates than there are in mocked outputs.'
    assert len(existing_product_certificates) == 1, fail_description
    fail_description = 'Library failed to identify certificate from mocked outputs.'
    assert existing_product_certificates[0] == '/etc/pki/product-default/cert', fail_description
