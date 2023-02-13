import functools
import logging

import pytest

from leapp.libraries.actor import setuptargetrepos_repomap
from leapp.libraries.actor.setuptargetrepos_repomap import get_default_repository_channels, RepoMapDataHandler
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import PESIDRepositoryEntry, RepoMapEntry, RepositoriesMapping


def make_pesid_repo(pesid, major_version, repoid, arch='x86_64', repo_type='rpm', channel='ga', rhui=''):
    """
    PESIDRepositoryEntry factory function allowing shorter data description in tests by providing default values.
    """
    return PESIDRepositoryEntry(
        pesid=pesid,
        major_version=major_version,
        repoid=repoid,
        arch=arch,
        repo_type=repo_type,
        channel=channel,
        rhui=rhui
    )


@pytest.fixture
def repomap_data_for_pesid_repo_retrieval():
    # NOTE: do not change order or repositories; particular unit-tests tests
    # use specific repositories for the comparison, expecting them on the right
    # position in the list
    repomap_data = RepositoriesMapping(
        mapping=[
            RepoMapEntry(source='pesid1', target=['pesid3', 'pesid2']),
            RepoMapEntry(source='pesid4', target=['pesid4']),
        ],
        repositories=[
            make_pesid_repo('pesid1', '7', 'pesid1-repoid'),
            make_pesid_repo('pesid1', '7', 'pesid1-repoid-eus', channel='eus'),
            make_pesid_repo('pesid2', '8', 'pesid2-repoid'),
            make_pesid_repo('pesid3', '8', 'pesid3-repoid'),
            make_pesid_repo('pesid3', '8', 'pesid3-repoid-eus', channel='eus'),
            make_pesid_repo('pesid3', '8', 'pesid3-repoid-aws', rhui='aws'),
            make_pesid_repo('pesid4', '7', 'pesid4-repoid1'),
            make_pesid_repo('pesid4', '8', 'pesid4-repoid2'),
        ]
    )
    return repomap_data


def test_get_pesid_repo_entry(monkeypatch, repomap_data_for_pesid_repo_retrieval):
    """
    Test for the RepoMapDataHandler.get_pesid_repo_entry method.

    Verifies that the method correctly retrieves PESIDRepositoryEntry that are matching the OS major version
    and repoid.
    """
    monkeypatch.setattr(api, 'current_actor',
                        CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4'))
    repositories = repomap_data_for_pesid_repo_retrieval.repositories
    handler = RepoMapDataHandler(repomap_data_for_pesid_repo_retrieval)

    fail_description = (
        'get_pesid_repo_entry method failed to find correct pesid repository that matches given parameters.')
    for exp_repo in repositories:
        result_repo = handler.get_pesid_repo_entry(exp_repo.repoid, exp_repo.major_version)
        assert result_repo == exp_repo, fail_description

    fail_description = (
        'get_pesid_repo_entry method found a pesid repository, but no repository should match given parameters.')
    assert handler.get_pesid_repo_entry('pesid1-repoid', '6') is None, fail_description
    assert handler.get_pesid_repo_entry('pesid1-repoid', '8') is None, fail_description
    assert handler.get_pesid_repo_entry('pesid1-repoid', '9') is None, fail_description
    assert handler.get_pesid_repo_entry('nonexisting-repo', '7') is None, fail_description


def test_get_target_pesids(monkeypatch, repomap_data_for_pesid_repo_retrieval):
    """
    Test for the RepoMapDataHandler.get_target_pesids method.

    Verifies that the method correctly tells what target pesids is the given source pesid mapped to.
    """
    monkeypatch.setattr(api, 'current_actor',
                        CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4'))
    handler = RepoMapDataHandler(repomap_data_for_pesid_repo_retrieval)

    expected_target_pesids = ['pesid2', 'pesid3']
    actual_target_pesids = handler.get_target_pesids('pesid1')

    fail_description = (
        'The get_target_pesids method did not correctly identify what is the given source pesid mapped to.')
    assert expected_target_pesids == actual_target_pesids, fail_description

    fail_description = (
        'The get_target_pesids method found target pesids even if the source repository is not mapped.')
    assert [] == handler.get_target_pesids('pesid2'), fail_description
    assert [] == handler.get_target_pesids('pesid_no_mapping'), fail_description


def test_get_pesid_repos(monkeypatch, repomap_data_for_pesid_repo_retrieval):
    """
    Test for the RepoMapDataHandler.get_pesid_repos method.

    Verifies that the method is able to collect all PESIDRepositoryEntry present in the repomap data that
    match the given OS major version and the given pesid.
    """
    monkeypatch.setattr(api, 'current_actor',
                        CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4'))
    handler = RepoMapDataHandler(repomap_data_for_pesid_repo_retrieval)
    repositories = repomap_data_for_pesid_repo_retrieval.repositories

    actual_pesid_repos = handler.get_pesid_repos('pesid3', '8')
    expected_pesid_repos = [repositories[3], repositories[4], repositories[5]]
    fail_description = 'The get_pesid_repos failed to find pesid repos matching the given criteria.'
    assert len(expected_pesid_repos) == len(actual_pesid_repos), fail_description
    for actual_pesid_repo in actual_pesid_repos:
        assert actual_pesid_repo in expected_pesid_repos, fail_description

    actual_pesid_repos = handler.get_pesid_repos('pesid1', '7')
    expected_pesid_repos = [repositories[0], repositories[1]]
    assert len(expected_pesid_repos) == len(actual_pesid_repos), fail_description
    for actual_pesid_repo in actual_pesid_repos:
        assert actual_pesid_repo in expected_pesid_repos, fail_description

    fail_description = (
        'The get_pesid_repos found some pesid repositories matching criteria, but there are no such repositories.')
    assert [] == handler.get_pesid_repos('pesid3', '7'), fail_description
    assert [] == handler.get_pesid_repos('pesid1', '8'), fail_description
    assert [] == handler.get_pesid_repos('nonexisting_pesid', '7'), fail_description


def test_get_source_pesid_repos(monkeypatch, repomap_data_for_pesid_repo_retrieval):
    """
    Test for the RepoMapDataHandler.get_source_pesid_repos method.

    Verifies that the method is able to collect all PESIDRepositoryEntry that match the given PES ID and
    have the major version same as the source system.
    """
    monkeypatch.setattr(api, 'current_actor',
                        CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4'))
    handler = RepoMapDataHandler(repomap_data_for_pesid_repo_retrieval)
    repositories = repomap_data_for_pesid_repo_retrieval.repositories

    fail_description = (
        'The get_source_pesid_repos method failed to retrieve all pesid repos that match given pesid '
        'and have the major version same as the source system.')
    expected_pesid_repos = [repositories[0], repositories[1]]
    actual_pesid_repos = handler.get_source_pesid_repos('pesid1')
    assert len(expected_pesid_repos) == len(actual_pesid_repos), fail_description
    for actual_pesid_repo in actual_pesid_repos:
        assert actual_pesid_repo in expected_pesid_repos, fail_description

    fail_description = (
        'The get_source_pesid_repos method does not take into account the source system version correctly.'
    )
    monkeypatch.setattr(setuptargetrepos_repomap, 'get_source_major_version', lambda: '10')

    # Repeat the same test as above to make sure it respects the source OS major version
    assert [] == handler.get_source_pesid_repos('pesid1'), fail_description

    assert [] == handler.get_source_pesid_repos('pesid2'), fail_description
    assert [] == handler.get_source_pesid_repos('nonexisting_pesid'), fail_description


def test_get_target_pesid_repos(monkeypatch, repomap_data_for_pesid_repo_retrieval):
    """
    Test for the RepoMapDataHandler.get_target_pesid_repos method.

    Verifies that the method is able to collect all PESIDRepositoryEntry that match the given PES ID and
    have the major version same as the source system.
    """
    monkeypatch.setattr(api, 'current_actor',
                        CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4'))
    handler = RepoMapDataHandler(repomap_data_for_pesid_repo_retrieval)
    repositories = repomap_data_for_pesid_repo_retrieval.repositories

    fail_description = (
        'The get_target_pesid_repos method failed to retrieve all pesid repos that match given pesid '
        'and have the major version same as the target system.')
    expected_pesid_repos = [repositories[3], repositories[4], repositories[5]]
    actual_pesid_repos = handler.get_target_pesid_repos('pesid3')
    assert len(expected_pesid_repos) == len(actual_pesid_repos), fail_description
    for actual_pesid_repo in actual_pesid_repos:
        assert actual_pesid_repo in expected_pesid_repos, fail_description

    fail_description = (
        'The get_target_pesid_repos method doesn\'t take into account the target system version correctly.'
    )
    monkeypatch.setattr(api, 'current_actor',
                        CurrentActorMocked(arch='x86_64', src_ver='9.4', dst_ver='10.0'))

    # Repeat the same test as above to make sure it respects the target OS major version
    assert [] == handler.get_target_pesid_repos('pesid3'), fail_description

    assert [] == handler.get_target_pesid_repos('pesid1'), fail_description
    assert [] == handler.get_target_pesid_repos('nonexisting_pesid'), fail_description


@pytest.fixture
def mapping_data_for_find_repository_equiv():
    repositories = [
        make_pesid_repo('pesid1', '7', 'pesid1-repoid'),
        make_pesid_repo('pesid1', '7', 'pesid1-repoid', channel='e4s', rhui='aws'),
        make_pesid_repo('pesid2', '8', 'pesid2-repoid1'),
        make_pesid_repo('pesid2', '8', 'pesid2-repoid2-s390x', arch='s390x'),
        # This repository is a better candidate than the full match equivalent, but _find_repository_target_equivalent
        # should not take into account channel priorities
        make_pesid_repo('pesid2', '8', 'pesid2-repoid2', arch='x86_64', channel='eus'),
        make_pesid_repo('pesid2', '8', 'pesid2-repoid3-srpm', repo_type='srpm'),
        make_pesid_repo('pesid2', '8', 'pesid2-repoid4.1', rhui='aws'),
        make_pesid_repo('pesid2', '8', 'pesid2-repoid4.2', channel='eus', rhui='aws'),
        make_pesid_repo('pesid3', '8', 'pesid3-repoid')
    ]
    return RepositoriesMapping(
        mapping=[RepoMapEntry(source='pesid1', target=['pesid2', 'pesid3'])],
        repositories=repositories
    )


def test_find_repository_target_equivalent_fullmatch(monkeypatch, mapping_data_for_find_repository_equiv):
    """
    Test for the RepoMapDataHandler._find_repository_target_equivalent method.

    Verifies that the method can find the target equivalent for a repository that matches the source
    pesid repo parameters exactly when such repository is available in the repository mapping data.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4'))

    handler = RepoMapDataHandler(mapping_data_for_find_repository_equiv)

    expected_target_equivalent = mapping_data_for_find_repository_equiv.repositories[2]
    actual_target_equivalent = handler._find_repository_target_equivalent(
        mapping_data_for_find_repository_equiv.repositories[0], 'pesid2')

    fail_description = (
        'The _find_repository_target_equivalent failed to find equivalent that exactly matched the source pesid repo '
        'when there is such equivalent available in the repository mapping data.')
    assert expected_target_equivalent == actual_target_equivalent, fail_description


def test_find_repository_target_equivalent_fallback_to_default(monkeypatch,
                                                               mapping_data_for_find_repository_equiv):
    """
    Test for the RepoMapDataHandler._find_repository_target_equivalent method.

    Verifies that the method will find a target equivalent with matching some of the fallback
    channels if a target equivalent that matches the source pesid repository completely is not
    available in the repository mapping data.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4'))

    handler = RepoMapDataHandler(mapping_data_for_find_repository_equiv)
    repositories = mapping_data_for_find_repository_equiv.repositories

    fail_description = (
        'The _find_repository_target_equivalent failed to find repository with some of the fallback channels.')
    expected_target_equivalent = repositories[6]
    actual_target_equivalent = handler._find_repository_target_equivalent(repositories[1], 'pesid2')
    assert expected_target_equivalent == actual_target_equivalent, fail_description

    handler.set_default_channels(['eus', 'ga'])

    expected_target_equivalent = repositories[7]
    actual_target_equivalent = handler._find_repository_target_equivalent(repositories[1], 'pesid2')
    assert expected_target_equivalent == actual_target_equivalent, fail_description


def test_find_repository_target_equivalent_no_target_equivalent(monkeypatch,
                                                                mapping_data_for_find_repository_equiv):
    """
    Test for the RepoMapDataHandler._find_repository_target_equivalent method.

    Verifies that the  does not crash when there is no target repository that is equivalent to the
    source repository.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='s390x', src_ver='7.9', dst_ver='8.4'))
    handler = RepoMapDataHandler(mapping_data_for_find_repository_equiv)

    fail_description = 'The _find_repository_target_equivalent found target equivalent when there are none.'

    repository_with_no_equivalent = make_pesid_repo('pesid1', '7', 'pesid1-some-repoid', arch='s390x', rhui='aws')
    target_equivalent = handler._find_repository_target_equivalent(repository_with_no_equivalent, 'pesid2')
    assert target_equivalent is None, fail_description


def test_get_mapped_target_pesid_repos(monkeypatch, mapping_data_for_find_repository_equiv):
    """
    Test for the RepoMapDataHandler.get_mapped_target_pesid_repos method.

    Verifies that the method correctly builds a map mapping the target pesid to the best candidate
    pesid repos.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4'))
    repositories = mapping_data_for_find_repository_equiv.repositories

    handler = RepoMapDataHandler(mapping_data_for_find_repository_equiv)

    # Both pesid2 and pesid3 have an equivalent for provided source pesid repository
    fail_description = (
        'The get_mapped_target_pesid_repos failed to build a map mapping the target pesid '
        'to the best pesid repository candidate.')
    target_pesid_repos_map = handler.get_mapped_target_pesid_repos(repositories[0])
    expected_pesid_to_best_candidate_map = {'pesid2': repositories[2], 'pesid3': repositories[8]}
    assert target_pesid_repos_map == expected_pesid_to_best_candidate_map, fail_description

    # The pesid3 does not have an equivalent for provided source pesid repository (due to not having any rhui repos)
    target_pesid_repos_map = handler.get_mapped_target_pesid_repos(repositories[1])
    expected_pesid_to_best_candidate_map = {'pesid2': repositories[6], 'pesid3': None}
    assert target_pesid_repos_map == expected_pesid_to_best_candidate_map, fail_description


def test_get_mapped_target_repoids(monkeypatch, mapping_data_for_find_repository_equiv):
    """
    Test for the RepoMapDataHandler.get_mapped_target_repoids method.

    Verifies that the method returns a correct list of repoids that should be present on the target system.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4'))

    handler = RepoMapDataHandler(mapping_data_for_find_repository_equiv)
    repositories = mapping_data_for_find_repository_equiv.repositories

    fail_description = (
        'The get_mapped_target_repoids method failed to return the correct list of repoids ',
        'to be enabled on the target system.')
    # Both pesid2 and pesid3 have an equivalent for provided source pesid repository
    actual_target_repoids = handler.get_mapped_target_repoids(repositories[0])
    expected_target_repoids = {repositories[2].repoid, repositories[8].repoid}
    assert len(actual_target_repoids) == len(expected_target_repoids), fail_description
    assert set(actual_target_repoids) == expected_target_repoids, fail_description

    # The pesid3 does not have an equivalent for provided source pesid
    # repository -> only one repository should be in the produced list
    actual_target_repoids = handler.get_mapped_target_repoids(repositories[1])
    assert len(actual_target_repoids) == 1
    assert 'pesid2-repoid4.1' in actual_target_repoids, fail_description


def test_get_expected_target_repoids_simple(monkeypatch):
    """
    Test for the RepoMapDataHandler.get_expected_target_repoids method.

    Verifies that the method is able to produce a correct map that maps target pesid to the best
    candidate pesid repository when there is only one repoid enabled and the corresponding source
    pesid repository has exact match target equivalent.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4'))

    repositories_mapping = RepositoriesMapping(
        mapping=[RepoMapEntry(source='pesid1', target=['pesid2'])],
        repositories=[
            make_pesid_repo('pesid1', '7', 'pesid1-repoid'),
            make_pesid_repo('pesid2', '8', 'pesid2-repoid')
        ]
    )
    fail_description = 'Failed to get_expected_target_repoids with only one repository enabled on the source system.'
    handler = RepoMapDataHandler(repositories_mapping)
    target_repoids = handler.get_expected_target_pesid_repos(['pesid1-repoid'])

    assert {'pesid2': repositories_mapping.repositories[1]} == target_repoids, fail_description


def test_get_expected_target_repoids_best_candidate_produced(monkeypatch):
    """
    Test for the RepoMapDataHandler.get_expected_target_repoids method.

    Verifies that the method is able to produce a correct map that maps target pesid to the best
    candidate pesid repository when there are two repositories with different priority channels
    belonging to the same pesid family enabled on the source system and both have target
    equivalents.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4'))

    repositories_mapping = RepositoriesMapping(
        mapping=[RepoMapEntry(source='pesid1', target=['pesid2'])],
        repositories=[
            make_pesid_repo('pesid1', '7', 'pesid1-repoid-ga'),
            make_pesid_repo('pesid1', '7', 'pesid1-repoid-eus', channel='eus'),
            make_pesid_repo('pesid2', '8', 'pesid2-repoid-ga'),
            make_pesid_repo('pesid2', '8', 'pesid2-repoid-eus', channel='eus'),
            make_pesid_repo('pesid2', '8', 'pesid2-repoid-e4s', channel='e4s'),
        ]
    )

    handler = RepoMapDataHandler(repositories_mapping)
    target_repoids = handler.get_expected_target_pesid_repos(['pesid1-repoid-eus'])

    fail_description = (
        'The get_expected_target_repoids failed to map target pesid to a pesid repository'
        'with the highest priority channel.'
    )
    assert {'pesid2': repositories_mapping.repositories[3]} == target_repoids, fail_description


def test_get_expected_target_repoids_fallback(monkeypatch):
    """
    Test for the RepoMapDataHandler.get_expected_target_repoids method.

    Verifies that the RepoMapDataHandler.get_expected_target_repoids method is able to produce a correct
    map that maps target pesid to the best candidate pesid repository when there is a repository
    on the source system that does not have exact match equivalent and some other with a fallback channel
    must be found.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4'))

    repositories_mapping = RepositoriesMapping(
        mapping=[RepoMapEntry(source='pesid1', target=['pesid2'])],
        repositories=[
            make_pesid_repo('pesid1', '7', 'pesid1-repoid-eus', channel='eus'),
            make_pesid_repo('pesid2', '8', 'pesid2-repoid-ga'),
            make_pesid_repo('pesid1', '8', 'pesid2-repoid-e4s', channel='e4s'),
        ]
    )

    fail_description = (
        'The get_expected_target_repoids failed to find repository with a failback channel '
        'since there were no exact target equivalents.')

    handler = RepoMapDataHandler(repositories_mapping)
    handler.set_default_channels(['ga'])
    target_repoids = handler.get_expected_target_pesid_repos(['pesid1-repoid-eus'])

    assert {'pesid2': repositories_mapping.repositories[1]} == target_repoids, fail_description


def test_get_expected_target_pesid_repos_multiple_repositories(monkeypatch):
    """
    Test for the RepoMapDataHandler.get_expected_target_repoids method.

    Verifies that the RepoMapDataHandler.get_expected_target_repoids method is able to produce a correct
    map that maps target pesid to the best candidate pesid repository when one source pesid is mapped
    to multiple target pesids (every target pesid should have an entry in the returned map).
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4'))

    repositories_mapping = RepositoriesMapping(
        mapping=[RepoMapEntry(source='pesid1', target=['pesid2', 'pesid3'])],
        repositories=[
            make_pesid_repo('pesid1', '7', 'pesid1-repoid-ga'),
            make_pesid_repo('pesid2', '8', 'pesid2-repoid-ga'),
            make_pesid_repo('pesid3', '8', 'pesid3-repoid-ga')
        ]
    )

    fail_description = 'Failed to get_expected_target_repoids when one source pesid is mapped to two target pesids.'
    handler = RepoMapDataHandler(repositories_mapping)
    target_repoids = handler.get_expected_target_pesid_repos(['pesid1-repoid-ga'])

    assert {'pesid2': repositories_mapping.repositories[1],
            'pesid3': repositories_mapping.repositories[2]} == target_repoids, fail_description


def test_get_expected_target_pesid_repos_unmapped_repository(monkeypatch):
    """
    Test for the RepoMapDataHandler.get_expected_target_repoids method.

    Verifies that the RepoMapDataHandler.get_expected_target_repoids method does not fail
    when there is a repository on the source system that is not mapped.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4'))

    repositories_mapping = RepositoriesMapping(
        mapping=[RepoMapEntry(source='pesid1', target=['pesid2'])],
        repositories=[
            make_pesid_repo('pesid1', '7', 'pesid1-repoid-ga'),
            make_pesid_repo('pesid2', '8', 'pesid2-repoid-ga')
        ])

    fail_description = 'Failed to get_expected_target_repoids when one of the source repoids is unmapped.'
    handler = RepoMapDataHandler(repositories_mapping)
    target_repoids = handler.get_expected_target_pesid_repos(['pesid1-repoid-ga', 'unmapped-repoid'])

    assert {'pesid2': repositories_mapping.repositories[1]} == target_repoids, fail_description


def test_get_expected_target_pesid_repos_repo_with_no_equivalent(monkeypatch, caplog):
    """
    Test for the RepoMapDataHandler.get_expected_target_repoids method.

    Verifies that the RepoMapDataHandler.get_expected_target_repoids method does not fail
    when there is a repository on the source system that does not have any equivalents.
    A warning should be produced when a situation like this occurs.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4'))

    repositories_mapping = RepositoriesMapping(
        mapping=[RepoMapEntry(source='pesid1', target=['pesid2'])],
        repositories=[
            make_pesid_repo('pesid1', '7', 'pesid1-repoid-ga'),
            make_pesid_repo('pesid2', '8', 'pesid2-repoid-eus', channel='eus'),
        ]
    )

    handler = RepoMapDataHandler(repositories_mapping)
    target_repoids = handler.get_expected_target_pesid_repos(['pesid1-repoid-ga'])

    fail_description = (
        'Failed get_expected_target_repoids with a source repository that does not have any target equivalent.')
    assert {'pesid2': None} == target_repoids, fail_description
    missing_target_equivalent_message = (
        'Cannot find any mapped target repository from the pesid2 family for the pesid1-repoid-ga repository.'
    )

    # A warning should be produced when a target equivalent was not found.
    warning_produced = False
    for record in caplog.records:
        if record.levelno == logging.WARNING and record.message == missing_target_equivalent_message:
            warning_produced = True
            break
    assert warning_produced, 'A warning should be produced when a repository has no equivalent.'


def test_get_default_repository_channels_simple(monkeypatch):
    """
    Test for the get_default_repository_channels function.

    Verifies that the function returns correct list of default channels on a source system
    where there is only one repository enabled from the pesid family in which are
    the default repositories searched in.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4'))
    repository_mapping = RepositoriesMapping(
        mapping=[],
        repositories=[make_pesid_repo('rhel7-base', '7', 'rhel7-repoid-ga', channel='ga')]
    )
    handler = RepoMapDataHandler(repository_mapping)

    assert ['ga'] == get_default_repository_channels(handler, ['rhel7-repoid-ga'])


def test_get_default_repository_channels_highest_priority_channel(monkeypatch):
    """
    Test for the get_default_repository_channels function.

    Verifies that the returned list contains the highest priority channel if there is a repository
    with the channel enabled on the source system.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4'))
    repository_mapping = RepositoriesMapping(
        mapping=[],
        repositories=[
            make_pesid_repo('rhel7-base', '7', 'rhel7-repoid-ga', channel='ga'),
            make_pesid_repo('rhel7-base', '7', 'rhel7-repoid-eus', channel='eus'),
        ]
    )
    handler = RepoMapDataHandler(repository_mapping)

    assert ['eus', 'ga'] == get_default_repository_channels(handler, ['rhel7-repoid-ga', 'rhel7-repoid-eus'])


def test_get_default_repository_channels_no_default_pesid_repo(monkeypatch):
    """
    Test for the get_default_repository_channels function.

    Verifies that the returned list contains some fallback channel even if no repository from the default
    pesid family in which are the channels searched is enabled.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4'))
    repository_mapping = RepositoriesMapping(
        mapping=[],
        repositories=[
            make_pesid_repo('rhel7-base', '7', 'rhel7-repoid-ga', channel='ga'),
            make_pesid_repo('rhel7-base', '7', 'rhel7-repoid-eus', channel='eus'),
        ]
    )
    handler = RepoMapDataHandler(repository_mapping)

    assert ['ga'] == get_default_repository_channels(handler, ['some-repoid'])


def test_find_repository_equivalent_with_priority_channel(monkeypatch):
    """
    Tests whether the _find_repository_target_equivalent correctly respects the chosen preferred channel.
    """
    envars = {'LEAPP_DEVEL_TARGET_PRODUCT_TYPE': 'eus'}

    monkeypatch.setattr(api, 'current_actor',
                        CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4', envars=envars))
    repositories_mapping = RepositoriesMapping(
        mapping=[RepoMapEntry(source='pesid1', target=['pesid2'])],
        repositories=[
            make_pesid_repo('pesid1', '7', 'pesid1-repoid-ga'),
            make_pesid_repo('pesid2', '8', 'pesid2-repoid-ga', channel='ga'),
            make_pesid_repo('pesid2', '8', 'pesid2-repoid-eus', channel='eus'),
        ]
    )

    handler = RepoMapDataHandler(repositories_mapping)
    handler.set_default_channels(['ga'])

    assert handler.prio_channel == 'eus'

    fail_description = '_find_repository_target_equivalent does not correctly respect preferred channel.'
    expected_target_equivalent = repositories_mapping.repositories[2]
    actual_target_equivalent = handler._find_repository_target_equivalent(repositories_mapping.repositories[0],
                                                                          'pesid2')
    assert expected_target_equivalent == actual_target_equivalent, fail_description


def test_get_expected_target_pesid_repos_with_priority_channel_set(monkeypatch):
    """
    Tests whether the get_expected_target_peid_repos correctly respects the chosen preferred channel.
    """

    envars = {'LEAPP_DEVEL_TARGET_PRODUCT_TYPE': 'eus'}

    monkeypatch.setattr(api, 'current_actor',
                        CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.4', envars=envars))

    repositories_mapping = RepositoriesMapping(
        mapping=[RepoMapEntry(source='pesid1', target=['pesid2', 'pesid3'])],
        repositories=[
            make_pesid_repo('pesid1', '7', 'pesid1-repoid-ga'),
            make_pesid_repo('pesid2', '8', 'pesid2-repoid-ga'),
            make_pesid_repo('pesid2', '8', 'pesid2-repoid-eus', channel='eus'),
            make_pesid_repo('pesid2', '8', 'pesid2-repoid-tuv', channel='tuv'),
            make_pesid_repo('pesid3', '8', 'pesid3-repoid-ga')
        ]
    )

    handler = RepoMapDataHandler(repositories_mapping)
    # Set defaults to verify that the priority channel is not overwritten by defaults
    handler.set_default_channels(['tuv', 'ga'])
    target_repoids = handler.get_expected_target_pesid_repos(['pesid1-repoid-ga'])

    fail_description = 'get_expected_target_peid_repos does not correctly respect preferred channel.'
    assert {'pesid2': repositories_mapping.repositories[2],
            'pesid3': repositories_mapping.repositories[4]} == target_repoids, fail_description


@pytest.mark.parametrize('rhui', ('', 'aws', 'aws-sap-e4s', 'azure', 'azure-sap-ha', 'azure-sap-apps'))
def test_multiple_repoids_in_repomapping(monkeypatch, rhui):
    """
    Tests whether a correct repository is selected when running on cloud with multiple repositories having the same ID.

    In such a case, the actor should use the cloud provider as a guide on which of the repositores should it pick.
    """

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64', src_ver='7.9', dst_ver='8.6'))

    mk_rhui_el7_pesid_repo = functools.partial(PESIDRepositoryEntry,
                                               pesid='rhel7-rhui',
                                               major_version='7',
                                               repoid='repoid7-rhui',
                                               repo_type='rpm',
                                               arch='x86_64',
                                               channel='ga')

    mk_rhui_el8_pesid_repo = functools.partial(PESIDRepositoryEntry,
                                               pesid='rhel8-rhui',
                                               major_version='8',
                                               repo_type='rpm',
                                               arch='x86_64',
                                               channel='ga')

    repomap = RepositoriesMapping(
        mapping=[RepoMapEntry(source='rhel7-rhui', target=['rhel8-rhui'])],
        repositories=[
            mk_rhui_el7_pesid_repo(rhui=''),
            mk_rhui_el7_pesid_repo(rhui='aws'),
            mk_rhui_el7_pesid_repo(rhui='azure'),
            mk_rhui_el8_pesid_repo(repoid='repoid8-rhui', rhui=''),
            mk_rhui_el8_pesid_repo(repoid='repoid8-rhui-aws', rhui='aws'),
            mk_rhui_el8_pesid_repo(repoid='repoid8-rhui-azure', rhui='azure'),
        ]
    )

    handler = RepoMapDataHandler(repomap, cloud_provider=rhui)
    target_repoids = handler.get_expected_target_pesid_repos(['repoid7-rhui'])

    assert len(target_repoids) == 1

    expected_suffixes = {
        '': '',
        'aws': '-aws',
        'aws-sap-e4s': '-aws',
        'azure': '-azure',
        'azure-sap-apps': '-azure',
        'azure-sap-ha': '-azure'
    }

    assert 'rhel8-rhui' in target_repoids
    assert target_repoids['rhel8-rhui'].repoid == 'repoid8-rhui{0}'.format(expected_suffixes[rhui])
