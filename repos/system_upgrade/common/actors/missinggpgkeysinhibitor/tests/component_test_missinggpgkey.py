import pytest
from six.moves.urllib.error import URLError

from leapp import reporting
from leapp.exceptions import StopActorExecution
from leapp.libraries.actor import missinggpgkey
from leapp.libraries.actor.missinggpgkey import process, register_dnfworkaround
from leapp.libraries.common.gpg import GpgKeyInfo, GpgReadError
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    DNFWorkaround,
    GpgPubKey,
    RepositoriesFactsTarget,
    RepositoryData,
    RepositoryFile,
    TargetUserSpaceInfo,
    TrustedGpgKeys,
    UsedTargetRepositories,
    UsedTargetRepository
)

# Note, that this is not a real component test as described in the documentation,
# but basically unit test calling the "main" function process() to simulate the
# whole process as I was initially advised not to use these component tests.


@pytest.mark.parametrize('src_ver, should_register', [
    # < 9.7: no PQC keys exist, so the host-side workaround (rpm --import)
    # imports all trusted target keys directly
    ('8.10', True),
    ('9.6', True),
    # 9.7 <= source < 10.0: the source RPM stack cannot import PQC (v6) keys,
    # so a separate workaround runs in the target userspace to import them
    # However, full PQc can only be enabled on source >= 9.9, where 'sq' is available.
    ('9.7', True),
    ('9.8', True),
    ('9.9', False),
    ('9.10', False),
])
def test_register_dnfworkaround_source_version_gating(monkeypatch, src_ver, should_register):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver=src_ver))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    register_dnfworkaround()

    assert api.produce.called == (1 if should_register else 0)
    if should_register:
        assert isinstance(api.produce.model_instances[0], DNFWorkaround)


def _get_test_gpgkeys_missing():
    """
    Return list of Trusted GPG keys without the epel9 key we look for
    """
    return [
        # Red Hat release key 2
        GpgPubKey(short_keyid='fd431d51', fingerprint='567e347ad0044ade55ba8a5f199e2f91fd431d51', rpmdb=True),
        # Red Hat aux key 3
        GpgPubKey(short_keyid='5a6340b3', fingerprint='7e4624258c406535d56d6f135054e4a45a6340b3', rpmdb=True),
    ]


def _get_test_gpgkeys():
    """
    Return all the Trusted GPG keys for a test
    """
    epel_9_key = GpgPubKey(
        short_keyid='3228467c',
        fingerprint='ff8ad1344597106ece813b918a3872bf3228467c',
        rpmdb=True,
    )
    return TrustedGpgKeys(keys=[epel_9_key] + _get_test_gpgkeys_missing())


def _get_test_targuserspaceinfo(path='/'):
    """
    Test TargetUserSpaceInfo which is needed to access the files in container root dir
    """
    return TargetUserSpaceInfo(
        path=path,
        scratch='',
        mounts='',
    )


def _get_test_usedtargetrepositories_list():
    """
    All target userspace directories
    """
    return [
        UsedTargetRepository(
            repoid='BaseOS',
        ),
        UsedTargetRepository(
            repoid='AppStream',
        ),
        UsedTargetRepository(
            repoid='MyAnotherRepo',
        ),
    ]


def _get_test_usedtargetrepositories():
    """
    The UsedTargetRepositories containing all repositories
    """
    return UsedTargetRepositories(
        repos=_get_test_usedtargetrepositories_list()
    )


def _get_test_target_repofile():
    """
    The valid RepositoryFile containing valid BaseOS and AppStream repositories
    """
    return RepositoryFile(
        file='/etc/yum.repos.d/target_rhel.repo',
        data=[
            RepositoryData(
                repoid='BaseOS',
                name="RHEL BaseOS repository",
                baseurl="/whatever/",
                enabled=True,
                additional_fields='{"gpgkey":"file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release"}'
            ),
            RepositoryData(
                repoid='AppStream',
                name="RHEL AppStream repository",
                baseurl="/whatever/",
                enabled=True,
                additional_fields='{"gpgkey":"file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release"}'
            ),
        ],
    )


def _get_test_target_repofile_additional():
    """
    The custom target repofile containing "problematic" repositories
    """
    return RepositoryFile(
        file='/etc/yum.repos.d/my_target_rhel.repo',
        data=[
            RepositoryData(
                repoid='MyRepo',
                name="My repository",
                baseurl="/whatever/",
                enabled=False,
            ),
            RepositoryData(
                repoid='MyAnotherRepo',
                name="My another repository",
                baseurl="/whatever/",
                enabled=True,
                additional_fields='{"gpgkey":"file:///etc/pki/rpm-gpg/RPM-GPG-KEY-my-release"}'
            ),
        ],
    )


def _get_test_tmptargetrepositoriesfacts():
    """
    All target repositories facts
    """
    return RepositoriesFactsTarget(
        repositories=[
            _get_test_target_repofile(),
            _get_test_target_repofile_additional(),
        ],
    )


def test_perform_nogpgcheck(monkeypatch):
    """
    Executes the "main" function with the --nogpgcheck commandline switch

    This test should skip any checks and just log a message that no checks were executed
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        envars={'LEAPP_NOGPGCHECK': '1'},
        msgs=[
            _get_test_gpgkeys(),
            _get_test_usedtargetrepositories(),
            _get_test_tmptargetrepositoriesfacts(),
        ],
    ))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    process()

    assert api.produce.called == 0
    assert len(api.current_logger.warnmsg) == 1
    assert '--nogpgcheck option is used' in api.current_logger.warnmsg[0]


@pytest.mark.parametrize('msgs', [
    [],
    [_get_test_gpgkeys],
    [_get_test_usedtargetrepositories],
    [_get_test_tmptargetrepositoriesfacts],
    # These are just incomplete lists of required facts
    [_get_test_gpgkeys(), _get_test_usedtargetrepositories()],
    [_get_test_usedtargetrepositories(), _get_test_tmptargetrepositoriesfacts()],
    [_get_test_gpgkeys(), _get_test_tmptargetrepositoriesfacts()],
])
def test_perform_missing_facts(monkeypatch, msgs):
    """
    Executes the "main" function with missing required facts

    The missing facts (either RPM information, Target Repositories or their facts) cause
    the StopActorExecutionError excepction. But this should be rare as the required facts
    are clearly defined in the actor interface.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    # TODO: the gpg call should be mocked

    with pytest.raises(StopActorExecution):
        process()
    # nothing produced
    assert api.produce.called == 0
    # not skipped by --nogpgcheck
    assert len(api.current_logger.warnmsg) == 1
    assert "Missing TargetUserSpaceInfo data" in api.current_logger.warnmsg[0]


def _get_test_tmptargetrepositoriesfacts_partial():
    return [
        _get_test_gpgkeys(),
        _get_test_usedtargetrepositories(),
        RepositoriesFactsTarget(
            repositories=[
                _get_test_target_repofile(),
                # missing MyAnotherRepo
            ]
        )
    ]


def parse_gpg_key_from_file_mocked(key_path):
    if key_path == '/etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release':
        return [
            GpgKeyInfo(
                fingerprint='567e347ad0044ade55ba8a5f199e2f91fd431d51',
                short_keyid='fd431d51',
                is_pqc=False,
            ),
            GpgKeyInfo(
                fingerprint='7e4624258c406535d56d6f135054e4a45a6340b3',
                short_keyid='5a6340b3',
                is_pqc=False,
            ),
        ]
    if key_path == '/etc/pki/rpm-gpg/RPM-GPG-KEY-my-release':
        return [
            GpgKeyInfo(
                fingerprint='ff8ad1344597106ece813b918a3872bf3228467c',
                short_keyid='3228467c',
                is_pqc=False,
            ),
        ]
    return [
        GpgKeyInfo(
            fingerprint='acb5ee4e831c74bb7c168d27f55ad3fb5323552a',
            short_keyid='5323552a',
            is_pqc=False,
        ),
    ]


def test_perform_missing_some_repo_facts(monkeypatch):
    """
    Executes the "main" function with missing repositories facts

    This is misalignment in the provided facts UsedTargetRepositories and RepositoriesFactsTarget,
    where we miss some metadata that are required by the first message.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=_get_test_tmptargetrepositoriesfacts_partial())
    )
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(missinggpgkey, 'parse_gpg_key_from_file', parse_gpg_key_from_file_mocked)

    with pytest.raises(StopActorExecution):
        process()
    assert api.produce.called == 0
    assert reporting.create_report.called == 0


def _get_test_tmptargetrepositoriesfacts_https_unused():
    return [
        _get_test_targuserspaceinfo(),
        _get_test_gpgkeys(),
        _get_test_usedtargetrepositories(),
        RepositoriesFactsTarget(
            repositories=[
                _get_test_target_repofile(),
                _get_test_target_repofile_additional(),
                RepositoryFile(
                    file='/etc/yum.repos.d/internet.repo',
                    data=[
                        RepositoryData(
                            repoid='ExternalRepo',
                            name="External repository",
                            baseurl="/whatever/path",
                            enabled=True,
                            additional_fields='{"gpgkey":"https://example.com/rpm-gpg/key.gpg"}',
                        ),
                    ],
                )
            ],
        ),
    ]


def test_perform_https_gpgkey_unused(monkeypatch):
    """
    Executes the "main" function with repositories providing keys over internet

    The external repository is not listed in UsedTargetRepositories so the repository
    is not checked and we should not get any error here.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=_get_test_tmptargetrepositoriesfacts_https_unused()
    ))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(missinggpgkey, 'parse_gpg_key_from_file', parse_gpg_key_from_file_mocked)

    process()
    assert not api.current_logger.warnmsg
    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], DNFWorkaround)
    assert reporting.create_report.called == 0


def get_test_tmptargetrepositoriesfacts_https():
    return (
        _get_test_targuserspaceinfo(),
        _get_test_gpgkeys(),
        UsedTargetRepositories(
            repos=_get_test_usedtargetrepositories_list() + [
                UsedTargetRepository(
                    repoid='ExternalRepo',
                ),
            ]
        ),
        RepositoriesFactsTarget(
            repositories=[
                _get_test_target_repofile(),
                _get_test_target_repofile_additional(),
                RepositoryFile(
                    file='/etc/yum.repos.d/internet.repo',
                    data=[
                        RepositoryData(
                            repoid='ExternalRepo',
                            name="External repository",
                            baseurl="/whatever/path",
                            enabled=True,
                            additional_fields='{"gpgkey":"https://example.com/rpm-gpg/key.gpg"}',
                        ),
                    ],
                )
            ],
        ),
    )


def get_test_tmptargetrepositoriesfacts_ftp():
    return (
        _get_test_targuserspaceinfo(),
        _get_test_gpgkeys(),
        UsedTargetRepositories(
            repos=_get_test_usedtargetrepositories_list() + [
                UsedTargetRepository(
                    repoid='ExternalRepo',
                ),
            ]
        ),
        RepositoriesFactsTarget(
            repositories=[
                _get_test_target_repofile(),
                _get_test_target_repofile_additional(),
                RepositoryFile(
                    file='/etc/yum.repos.d/internet.repo',
                    data=[
                        RepositoryData(
                            repoid='ExternalRepo',
                            name="External repository",
                            baseurl="/whatever/path",
                            enabled=True,
                            additional_fields='{"gpgkey":"ftp://example.com/rpm-gpg/key.gpg"}',
                        ),
                    ],
                )
            ],
        ),
    )


def _urlretrive_mocked(url, filename=None, reporthook=None, data=None):
    return filename


def test_perform_https_gpgkey(monkeypatch):
    """
    Executes the "main" function with repositories providing keys over internet

    This produces an report.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=get_test_tmptargetrepositoriesfacts_https())
    )
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(missinggpgkey, 'parse_gpg_key_from_file', parse_gpg_key_from_file_mocked)
    monkeypatch.setattr('six.moves.urllib.request.urlretrieve', _urlretrive_mocked)

    process()
    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], DNFWorkaround)
    assert reporting.create_report.called == 1
    assert "Detected unknown GPG keys for target system repositories" in reporting.create_report.reports[0]['title']
    assert "https://example.com/rpm-gpg/key.gpg" in reporting.create_report.reports[0]['summary']


def _urlretrive_mocked_urlerror(url, filename=None, reporthook=None, data=None):
    raise URLError('error')


def test_perform_https_gpgkey_urlerror(monkeypatch):
    """
    Executes the "main" function with repositories providing keys over internet

    This results in warning message printed. Other than that, no report is still produced.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=get_test_tmptargetrepositoriesfacts_https())
    )
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(missinggpgkey, 'parse_gpg_key_from_file', parse_gpg_key_from_file_mocked)
    monkeypatch.setattr('six.moves.urllib.request.urlretrieve', _urlretrive_mocked_urlerror)

    process()
    assert len(api.current_logger.warnmsg) == 1
    assert 'Failed to download the gpgkey https://example.com/rpm-gpg/key.gpg:' in api.current_logger.warnmsg[0]
    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], DNFWorkaround)
    assert reporting.create_report.called == 1
    assert "Failed to download GPG key for target repository" in reporting.create_report.reports[0]['title']
    assert "https://example.com/rpm-gpg/key.gpg" in reporting.create_report.reports[0]['summary']


def test_perform_ftp_gpgkey(monkeypatch):
    """
    Executes the "main" function with repositories providing keys over internet

    This results in error message printed. Other than that, no report is still produced.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=get_test_tmptargetrepositoriesfacts_ftp())
    )
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(missinggpgkey, 'parse_gpg_key_from_file', parse_gpg_key_from_file_mocked)

    process()
    assert len(api.current_logger.errmsg) == 1
    assert 'Skipping unknown protocol for gpgkey ftp://example.com/rpm-gpg/key.gpg' in api.current_logger.errmsg[0]
    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], DNFWorkaround)
    assert reporting.create_report.called == 1
    assert 'GPG keys provided using unknown protocol' in reporting.create_report.reports[0]['title']
    assert 'ftp://example.com/rpm-gpg/key.gpg' in reporting.create_report.reports[0]['summary']


def get_test_data_missing_key():
    return [
        _get_test_targuserspaceinfo(),
        TrustedGpgKeys(keys=_get_test_gpgkeys_missing()),
        _get_test_usedtargetrepositories(),
        _get_test_tmptargetrepositoriesfacts(),
    ]


def test_perform_report(monkeypatch):
    """
    Executes the "main" function with missing keys

    This should result in report outlining what key mentioned in target repositories is missing.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=get_test_data_missing_key())
    )
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(missinggpgkey, 'parse_gpg_key_from_file', parse_gpg_key_from_file_mocked)

    process()
    assert not api.current_logger.warnmsg
    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], DNFWorkaround)
    assert reporting.create_report.called == 1
    assert "Detected unknown GPG keys for target system repositories" in reporting.create_report.reports[0]['title']
    assert "/etc/pki/rpm-gpg/RPM-GPG-KEY-my-release" in reporting.create_report.reports[0]['summary']


def get_test_data_no_gpg_data():
    return [
        _get_test_targuserspaceinfo(),
        _get_test_gpgkeys(),
        _get_test_usedtargetrepositories(),
        _get_test_tmptargetrepositoriesfacts(),
    ]


def test_perform_invalid_key(monkeypatch):
    """
    Executes the "main" function with a gpgkey not containing any GPG data

    This should result in report outlining what key does not contain any valid data.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=get_test_data_no_gpg_data())
    )
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    def parse_gpg_key_from_file_error(key_path):
        # the part after : is sq specific
        raise GpgReadError('Failed to read fingerprint from GPG key: Error EOF')

    monkeypatch.setattr(missinggpgkey, 'parse_gpg_key_from_file', parse_gpg_key_from_file_error)

    process()
    assert len(api.current_logger.warnmsg) == 2, api.current_logger.warnmsg
    # the tool failed, so the warning carries the error it reported
    assert 'Error EOF' in api.current_logger.warnmsg[0]
    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], DNFWorkaround)
    assert reporting.create_report.called == 1
    assert 'Failed to read GPG keys from provided key files' in reporting.create_report.reports[0]['title']
    assert 'file:///etc/pki/rpm-gpg/RPM-GPG-KEY-my-release' in reporting.create_report.reports[0]['summary']


def test_perform_key_file_without_keys(monkeypatch):
    """
    Executes the "main" function with a readable gpgkey file holding no keys

    The tool succeeds but finds no OpenPGP data, so it returns an empty list
    instead of raising. That is a distinct path from the tool failing, and it
    is the common case of a key file that got truncated or replaced by HTML.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=get_test_data_no_gpg_data())
    )
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    def parse_gpg_key_from_file_empty(key_path):
        return []

    monkeypatch.setattr(missinggpgkey, 'parse_gpg_key_from_file', parse_gpg_key_from_file_empty)

    process()
    assert len(api.current_logger.warnmsg) == 2, api.current_logger.warnmsg
    # no tool error to report here, unlike the raising path above
    assert all('Error EOF' not in msg for msg in api.current_logger.warnmsg)
    assert all('Cannot get any gpg key from the file' in msg for msg in api.current_logger.warnmsg)
    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], DNFWorkaround)
    assert reporting.create_report.called == 1
    assert 'Failed to read GPG keys from provided key files' in reporting.create_report.reports[0]['title']
    assert 'file:///etc/pki/rpm-gpg/RPM-GPG-KEY-my-release' in reporting.create_report.reports[0]['summary']


def get_test_data_gpgcheck_without_gpgkey():
    return [
        _get_test_targuserspaceinfo(),
        _get_test_gpgkeys(),
        UsedTargetRepositories(
            repos=_get_test_usedtargetrepositories_list() + [
                UsedTargetRepository(
                    repoid='InvalidRepo',
                ),
            ]
        ),
        RepositoriesFactsTarget(
            repositories=[
                _get_test_target_repofile(),
                _get_test_target_repofile_additional(),
                RepositoryFile(
                    file='/etc/yum.repos.d/invalid.repo',
                    data=[
                        RepositoryData(
                            repoid='InvalidRepo',
                            name="Invalid repository",
                            baseurl="/whatever/path",
                            enabled=True,
                            additional_fields='{"gpgcheck":"1"}',  # this should be default
                        ),
                    ],
                )
            ],
        ),
    ]


def test_perform_gpgcheck_without_gpgkey(monkeypatch):
    """
    Executes the "main" function with a repository containing a gpgcheck=1 without any gpgkey=

    This should result in report outlining that this configuration is not supported
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=get_test_data_gpgcheck_without_gpgkey())
    )
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(missinggpgkey, 'parse_gpg_key_from_file', parse_gpg_key_from_file_mocked)

    process()
    assert len(api.current_logger.warnmsg) == 1
    assert ('The gpgcheck for the InvalidRepo repository is enabled but gpgkey is not specified.'
            ' Cannot be checked.') in api.current_logger.warnmsg[0]
    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], DNFWorkaround)
    assert reporting.create_report.called == 1
    assert 'Inconsistent repository without GPG key' in reporting.create_report.reports[0]['title']
    assert 'InvalidRepo' in reporting.create_report.reports[0]['summary']
