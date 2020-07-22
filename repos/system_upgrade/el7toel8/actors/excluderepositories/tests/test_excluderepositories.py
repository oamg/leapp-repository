import pytest

from leapp.libraries.actor import excluderepositories
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    CustomTargetRepository,
    EnvVar,
    RepositoriesExcluded,
    RepositoriesFacts,
    RepositoriesMap,
    RepositoryData,
    RepositoryFile,
    RepositoryMap,
)


@pytest.mark.parametrize(
    'valid_opt_repoid,product_type',
    [
        ('rhel-7-optional-rpms', 'ga'),
        ('rhel-7-optional-beta-rpms', 'beta'),
        ('rhel-7-optional-htb-rpms', 'htb'),
    ],
)
def test_with_optionals(monkeypatch, valid_opt_repoid, product_type):
    all_opt_repoids = {
        'rhel-7-optional-rpms',
        'rhel-7-optional-beta-rpms',
        'rhel-7-optional-htb-rpms',
    }
    # set of repos that should not be marked as optionals
    non_opt_repoids = all_opt_repoids - {valid_opt_repoid} | {
        'rhel-7-blacklist-rpms'
    }

    mapping = [
        RepositoryMap(
            to_pes_repo='rhel-7-blacklist-rpms',
            from_repoid='rhel-7-blacklist-rpms',
            to_repoid='rhel-8-blacklist-rpms',
            from_minor_version='all',
            to_minor_version='all',
            arch='x86_64',
            repo_type='rpm',
        ),
    ]
    for repoid in all_opt_repoids:
        mapping.append(
            RepositoryMap(
                to_pes_repo='rhel-7-foobar-rpms',
                from_repoid=repoid,
                to_repoid='rhel-8-optional-rpms',
                from_minor_version='all',
                to_minor_version='all',
                arch='x86_64',
                repo_type='rpm',
            )
        )

    monkeypatch.setattr(
        api,
        'current_actor',
        CurrentActorMocked(
            envars={'LEAPP_DEVEL_SOURCE_PRODUCT_TYPE': product_type},
            msgs=(RepositoriesMap(repositories=mapping),),
        ),
    )
    optionals = set(excluderepositories._get_optional_repo_mapping().keys())
    assert {valid_opt_repoid} == optionals
    assert not non_opt_repoids & optionals


def test_without_optionals(monkeypatch):
    mapping = [
        RepositoryMap(
            to_pes_repo='rhel-7-foobar-rpms',
            from_repoid='rhel-7-foobar-rpms',
            to_repoid='rhel-8-foobar-rpms',
            from_minor_version='all',
            to_minor_version='all',
            arch='x86_64',
            repo_type='rpm',
        ),
        RepositoryMap(
            to_pes_repo='rhel-7-blacklist-rpms',
            from_repoid='rhel-7-blacklist-rpms',
            to_repoid='rhel-8-blacklist-rpms',
            from_minor_version='all',
            to_minor_version='all',
            arch='x86_64',
            repo_type='rpm',
        ),
    ]

    monkeypatch.setattr(
        api,
        'current_actor',
        CurrentActorMocked(msgs=(RepositoriesMap(repositories=mapping),)),
    )
    assert not excluderepositories._get_optional_repo_mapping()


def test_with_empty_optional_repo(monkeypatch):
    def repositories_mock(*model):
        repos_data = [
            RepositoryData(
                repoid='rhel-7-optional-rpms',
                name='RHEL 7 Server',
                enabled=False,
            )
        ]
        repos_files = [
            RepositoryFile(
                file='/etc/yum.repos.d/redhat.repo', data=repos_data
            )
        ]
        yield RepositoriesFacts(repositories=repos_files)

    monkeypatch.setattr(
        excluderepositories, '_get_optional_repo_mapping', lambda: {}
    )
    monkeypatch.setattr(api, 'consume', repositories_mock)
    assert not excluderepositories._get_repos_to_exclude()


def test_with_repo_disabled(monkeypatch):
    def repositories_mock(*model):
        repos_data = [
            RepositoryData(
                repoid='rhel-7-optional-rpms',
                name='RHEL 7 Server',
                enabled=False,
            )
        ]
        repos_files = [
            RepositoryFile(
                file='/etc/yum.repos.d/redhat.repo', data=repos_data
            )
        ]
        yield RepositoriesFacts(repositories=repos_files)

    monkeypatch.setattr(
        excluderepositories,
        '_get_optional_repo_mapping',
        lambda: {'rhel-7-optional-rpms': 'rhel-7'},
    )
    monkeypatch.setattr(api, 'consume', repositories_mock)
    disabled = excluderepositories._get_repos_to_exclude()
    assert 'rhel-7' in disabled


def test_with_repo_enabled(monkeypatch):
    def repositories_mock(*model):
        repos_data = [
            RepositoryData(repoid='rhel-7-optional-rpms', name='RHEL 7 Server')
        ]
        repos_files = [
            RepositoryFile(
                file='/etc/yum.repos.d/redhat.repo', data=repos_data
            )
        ]
        yield RepositoriesFacts(repositories=repos_files)

    monkeypatch.setattr(
        excluderepositories,
        '_get_optional_repo_mapping',
        lambda: {'rhel-7-optional-rpms': 'rhel-7'},
    )
    monkeypatch.setattr(api, 'consume', repositories_mock)
    assert not excluderepositories._get_repos_to_exclude()


@pytest.mark.parametrize('optional_repos_name', [('test',), ()])
def test_repositoriesexcluded_list_not_empty(
    monkeypatch, current_actor_context, optional_repos_name
):
    monkeypatch.setattr(
        excluderepositories,
        '_get_repos_to_exclude',
        lambda: optional_repos_name,
    )

    current_actor_context.run()
    if optional_repos_name:
        assert (
            current_actor_context.messages()[0]['type']
            == 'RepositoriesExcluded'
        )
        assert (
            current_actor_context.messages()[0]['message']['data']
            == '{"repoids": ["test"]}'
        )
        assert current_actor_context.messages()[1]['type'] == 'Report'
    else:
        assert not current_actor_context.messages()


@pytest.mark.parametrize(
    ('enabled_repo', 'exp_len_of_messages'),
    [
        ('codeready-builder-for-rhel-8-x86_64-rpms', 1),
        ('some_other_enabled_repo', 2),
        (None, 2),
    ],
)
def test_enablerepo_option(
    current_actor_context, monkeypatch, enabled_repo, exp_len_of_messages
):
    monkeypatch.setattr(
        excluderepositories, 'get_product_type', lambda x: 'ga'
    )

    if enabled_repo:
        current_actor_context.feed(CustomTargetRepository(repoid=enabled_repo))

    repos_data = [
        RepositoryData(
            repoid='rhel-7-server-optional-rpms',
            name='RHEL 7 Server',
            enabled=False,
        )
    ]
    repos_files = [
        RepositoryFile(file='/etc/yum.repos.d/redhat.repo', data=repos_data)
    ]
    current_actor_context.feed(RepositoriesFacts(repositories=repos_files))

    current_actor_context.feed(
        RepositoriesMap(
            repositories=(
                [
                    RepositoryMap(
                        to_pes_repo='rhel-7-server-optional-rpms',
                        from_repoid='rhel-7-server-optional-rpms',
                        to_repoid='codeready-builder-for-rhel-8-x86_64-rpms',
                        from_minor_version='all',
                        to_minor_version='all',
                        arch='x86_64',
                        repo_type='rpm',
                    ),
                ]
            )
        )
    )

    current_actor_context.run()
    assert len(current_actor_context.messages()) == exp_len_of_messages
