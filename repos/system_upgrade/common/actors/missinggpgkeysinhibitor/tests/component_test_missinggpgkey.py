import pytest
from six.moves.urllib.error import URLError

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor.missinggpgkey import _pubkeys_from_rpms, process
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    DNFWorkaround,
    InstalledRPM,
    Report,
    RepositoriesFacts,
    RepositoryData,
    RepositoryFile,
    RPM,
    TargetUserSpaceInfo,
    TMPTargetRepositoriesFacts,
    UsedTargetRepositories,
    UsedTargetRepository
)
from leapp.utils.deprecation import suppress_deprecation

# Note, that this is not a real component test as described in the documentation,
# but basically unit test calling the "main" function process() to simulate the
# whole process as I was initially advised not to use these component tests.


def _get_test_installedrpm_no_my_key():
    """
    Valid RPM packages missing the key we are looking for (epel9)
    """
    return [
        RPM(
            name='rpm',
            version='4.16.1.3',
            release='17.el9',
            epoch='0',
            packager='Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>',
            arch='x86_64',
            pgpsig='RSA/SHA256, Mon 08 Aug 2022 09:10:15 AM UTC, Key ID 199e2f91fd431d51',
            repository='BaseOS',
        ),
        RPM(
            name='gpg-pubkey',
            version='fd431d51',
            release='4ae0493b',
            epoch='0',
            packager='Red Hat, Inc. (release key 2) <security@redhat.com>',
            arch='noarch',
            pgpsig=''
        ),
        RPM(
            name='gpg-pubkey',
            version='5a6340b3',
            release='6229229e',
            epoch='0',
            packager='Red Hat, Inc. (auxiliary key 3) <security@redhat.com>',
            arch='noarch',
            pgpsig=''
        ),
    ]


def _get_test_installedrpm():
    """
    All test RPMS packages
    """
    return InstalledRPM(
        items=[
            RPM(
                name='gpg-pubkey',
                version='3228467c',
                release='613798eb',
                epoch='0',
                packager='Fedora (epel9) <epel@fedoraproject.org>',
                arch='noarch',
                pgpsig=''
            ),
        ] + _get_test_installedrpm_no_my_key(),
    )


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


@suppress_deprecation(TMPTargetRepositoriesFacts)
def _get_test_tmptargetrepositoriesfacts():
    """
    All target repositories facts
    """
    return TMPTargetRepositoriesFacts(
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
            _get_test_installedrpm(),
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
    [_get_test_installedrpm],
    [_get_test_usedtargetrepositories],
    [_get_test_tmptargetrepositoriesfacts],
    # These are just incomplete lists of required facts
    [_get_test_installedrpm(), _get_test_usedtargetrepositories()],
    [_get_test_usedtargetrepositories(), _get_test_tmptargetrepositoriesfacts()],
    [_get_test_installedrpm(), _get_test_tmptargetrepositoriesfacts()],
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

    with pytest.raises(StopActorExecutionError):
        process()
    # nothing produced
    assert api.produce.called == 0
    # not skipped by --nogpgcheck
    assert not api.current_logger.warnmsg


@suppress_deprecation(TMPTargetRepositoriesFacts)
def _get_test_tmptargetrepositoriesfacts_partial():
    return [
        _get_test_installedrpm(),
        _get_test_usedtargetrepositories(),
        TMPTargetRepositoriesFacts(
            repositories=[
                _get_test_target_repofile(),
                # missing MyAnotherRepo
            ]
        )
    ]


def _gpg_show_keys_mocked(key_path):
    """
    Get faked output from gpg reading keys.

    This is needed to get away from dependency on the filesystem
    """
    if key_path == '/etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release':
        return {
            'stdout': [
                'pub:-:4096:1:199E2F91FD431D51:1256212795:::-:::scSC::::::23::0:',
                'fpr:::::::::567E347AD0044ADE55BA8A5F199E2F91FD431D51:',
                ('uid:-::::1256212795::DC1CAEC7997B3575101BB0FCAAC6191792660D8F::'
                 'Red Hat, Inc. (release key 2) <security@redhat.com>::::::::::0:'),
                'pub:-:4096:1:5054E4A45A6340B3:1646863006:::-:::scSC::::::23::0:',
                'fpr:::::::::7E4624258C406535D56D6F135054E4A45A6340B3:',
                ('uid:-::::1646863006::DA7F68E3872D6E7BDCE05225E7EB5F3ACDD9699F::'
                 'Red Hat, Inc. (auxiliary key 3) <security@redhat.com>::::::::::0:'),
            ],
            'stderr': (),
            'exit_code': 0,
        }
    if key_path == '/etc/pki/rpm-gpg/RPM-GPG-KEY-my-release':  # actually epel9 key
        return {
            'stdout': [
                'pub:-:4096:1:8A3872BF3228467C:1631033579:::-:::escESC::::::23::0:',
                'fpr:::::::::FF8AD1344597106ECE813B918A3872BF3228467C:',
                ('uid:-::::1631033579::3EED52B2BDE50880047DB883C87B0FCAE458D111::'
                 'Fedora (epel9) <epel@fedoraproject.org>::::::::::0:'),
            ],
            'stderr': (),
            'exit_code': 0,
        }

    return {
        'stdout': [
            'pub:-:4096:1:F55AD3FB5323552A:1628617948:::-:::escESC::::::23::0:',
            'fpr:::::::::ACB5EE4E831C74BB7C168D27F55AD3FB5323552A:',
            ('uid:-::::1628617948::4830BB019772421B89ABD0BBE245B89C73BF053F::'
             'Fedora (37) <fedora-37-primary@fedoraproject.org>::::::::::0:'),
        ],
        'stderr': (),
        'exit_code': 0,
    }


def _get_pubkeys_mocked(installed_rpms):
    """
    This skips getting fps from files in container for simplification
    """
    return _pubkeys_from_rpms(installed_rpms)


def test_perform_missing_some_repo_facts(monkeypatch):
    """
    Executes the "main" function with missing repositories facts

    This is misalignment in the provided facts UsedTargetRepositories and TMPTargetRepositoriesFacts,
    where we miss some metadata that are required by the first message.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=_get_test_tmptargetrepositoriesfacts_partial())
    )
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr('leapp.libraries.actor.missinggpgkey._gpg_show_keys', _gpg_show_keys_mocked)

    with pytest.raises(StopActorExecutionError):
        process()
    assert api.produce.called == 0
    assert reporting.create_report.called == 0


@suppress_deprecation(TMPTargetRepositoriesFacts)
def _get_test_tmptargetrepositoriesfacts_https_unused():
    return [
        _get_test_targuserspaceinfo(),
        _get_test_installedrpm(),
        _get_test_usedtargetrepositories(),
        TMPTargetRepositoriesFacts(
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
    monkeypatch.setattr('leapp.libraries.actor.missinggpgkey._gpg_show_keys', _gpg_show_keys_mocked)
    monkeypatch.setattr('leapp.libraries.actor.missinggpgkey._get_pubkeys', _get_pubkeys_mocked)

    process()
    assert not api.current_logger.warnmsg
    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], DNFWorkaround)
    assert reporting.create_report.called == 0


@suppress_deprecation(TMPTargetRepositoriesFacts)
def get_test_tmptargetrepositoriesfacts_https():
    return (
        _get_test_targuserspaceinfo(),
        _get_test_installedrpm(),
        UsedTargetRepositories(
            repos=_get_test_usedtargetrepositories_list() + [
                UsedTargetRepository(
                    repoid='ExternalRepo',
                ),
            ]
        ),
        TMPTargetRepositoriesFacts(
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


@suppress_deprecation(TMPTargetRepositoriesFacts)
def get_test_tmptargetrepositoriesfacts_ftp():
    return (
        _get_test_targuserspaceinfo(),
        _get_test_installedrpm(),
        UsedTargetRepositories(
            repos=_get_test_usedtargetrepositories_list() + [
                UsedTargetRepository(
                    repoid='ExternalRepo',
                ),
            ]
        ),
        TMPTargetRepositoriesFacts(
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
    monkeypatch.setattr('leapp.libraries.actor.missinggpgkey._gpg_show_keys', _gpg_show_keys_mocked)
    monkeypatch.setattr('leapp.libraries.actor.missinggpgkey._get_pubkeys', _get_pubkeys_mocked)
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
    monkeypatch.setattr('leapp.libraries.actor.missinggpgkey._gpg_show_keys', _gpg_show_keys_mocked)
    monkeypatch.setattr('leapp.libraries.actor.missinggpgkey._get_pubkeys', _get_pubkeys_mocked)
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
    monkeypatch.setattr('leapp.libraries.actor.missinggpgkey._gpg_show_keys', _gpg_show_keys_mocked)
    monkeypatch.setattr('leapp.libraries.actor.missinggpgkey._get_pubkeys', _get_pubkeys_mocked)

    process()
    assert len(api.current_logger.errmsg) == 1
    assert 'Skipping unknown protocol for gpgkey ftp://example.com/rpm-gpg/key.gpg' in api.current_logger.errmsg[0]
    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], DNFWorkaround)
    assert reporting.create_report.called == 1
    assert 'GPG keys provided using unknown protocol' in reporting.create_report.reports[0]['title']
    assert 'ftp://example.com/rpm-gpg/key.gpg' in reporting.create_report.reports[0]['summary']


@suppress_deprecation(TMPTargetRepositoriesFacts)
def get_test_data_missing_key():
    return [
        _get_test_targuserspaceinfo(),
        InstalledRPM(items=_get_test_installedrpm_no_my_key()),
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
    monkeypatch.setattr('leapp.libraries.actor.missinggpgkey._gpg_show_keys', _gpg_show_keys_mocked)
    monkeypatch.setattr('leapp.libraries.actor.missinggpgkey._get_pubkeys', _get_pubkeys_mocked)

    process()
    assert not api.current_logger.warnmsg
    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], DNFWorkaround)
    assert reporting.create_report.called == 1
    assert "Detected unknown GPG keys for target system repositories" in reporting.create_report.reports[0]['title']
    assert "/etc/pki/rpm-gpg/RPM-GPG-KEY-my-release" in reporting.create_report.reports[0]['summary']


@suppress_deprecation(TMPTargetRepositoriesFacts)
def get_test_data_no_gpg_data():
    return [
        _get_test_targuserspaceinfo(),
        _get_test_installedrpm(),
        _get_test_usedtargetrepositories(),
        _get_test_tmptargetrepositoriesfacts(),
    ]


def _gpg_show_keys_mocked_my_empty(key_path):
    """
    Get faked output from gpg reading keys.

    This is needed to get away from dependency on the filesystem. This time, the key
    /etc/pki/rpm-gpg/RPM-GPG-KEY-my-release does not return any GPG data
    """
    if key_path == '/etc/pki/rpm-gpg/RPM-GPG-KEY-my-release':
        return {
            'stdout': (),
            'stderr': ('gpg: no valid OpenPGP data found.\n'),
            'exit_code': 2,
        }
    return _gpg_show_keys_mocked(key_path)


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
    monkeypatch.setattr('leapp.libraries.actor.missinggpgkey._gpg_show_keys', _gpg_show_keys_mocked_my_empty)
    monkeypatch.setattr('leapp.libraries.actor.missinggpgkey._get_pubkeys', _get_pubkeys_mocked)

    process()
    assert len(api.current_logger.warnmsg) == 1
    assert 'Cannot get any gpg key from the file' in api.current_logger.warnmsg[0]
    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], DNFWorkaround)
    assert reporting.create_report.called == 1
    assert 'Failed to read GPG keys from provided key files' in reporting.create_report.reports[0]['title']
    assert 'file:///etc/pki/rpm-gpg/RPM-GPG-KEY-my-release' in reporting.create_report.reports[0]['summary']


@suppress_deprecation(TMPTargetRepositoriesFacts)
def get_test_data_gpgcheck_without_gpgkey():
    return [
        _get_test_targuserspaceinfo(),
        _get_test_installedrpm(),
        UsedTargetRepositories(
            repos=_get_test_usedtargetrepositories_list() + [
                UsedTargetRepository(
                    repoid='InvalidRepo',
                ),
            ]
        ),
        TMPTargetRepositoriesFacts(
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
    monkeypatch.setattr('leapp.libraries.actor.missinggpgkey._gpg_show_keys', _gpg_show_keys_mocked)
    monkeypatch.setattr('leapp.libraries.actor.missinggpgkey._get_pubkeys', _get_pubkeys_mocked)

    process()
    assert len(api.current_logger.warnmsg) == 1
    assert ('The gpgcheck for the InvalidRepo repository is enabled but gpgkey is not specified.'
            ' Cannot be checked.') in api.current_logger.warnmsg[0]
    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], DNFWorkaround)
    assert reporting.create_report.called == 1
    assert 'Inconsistent repository without GPG key' in reporting.create_report.reports[0]['title']
    assert 'InvalidRepo' in reporting.create_report.reports[0]['summary']
