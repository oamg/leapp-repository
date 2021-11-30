import json
import os

import pytest
import requests

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import repositoriesmapping
from leapp.libraries.common import fetch
from leapp.libraries.common.config import architecture, version
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import PESIDRepositoryEntry

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def adjust_cwd():
    previous_cwd = os.getcwd()
    os.chdir(os.path.join(CUR_DIR, "./"))
    yield
    os.chdir(previous_cwd)


def test_scan_existing_valid_data(monkeypatch, adjust_cwd):
    """
    Tests whether an existing valid repomap file is loaded correctly.
    """

    with open('files/repomap_example.json') as repomap_file:
        data = json.load(repomap_file)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='7.9', dst_ver='8.4'))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    repositoriesmapping.scan_repositories(lambda dummy: data)

    assert api.produce.called, 'Actor did not produce any message when deserializing valid repomap data.'

    fail_description = 'Actor produced multiple messages, but only one was expected.'
    assert len(api.produce.model_instances) == 1, fail_description

    repo_mapping = api.produce.model_instances[0]

    # Verify that the loaded JSON data is matching the repomap file content
    # 1. Verify src_pesid -> target_pesids mappings are loaded and filtered correctly
    fail_description = 'Actor produced more mappings than there are source system relevant mappings in the test file.'
    assert len(repo_mapping.mapping) == 1, fail_description
    fail_description = 'Actor failed to load IPU-relevant mapping data correctly.'
    assert repo_mapping.mapping[0].source == 'pesid1', fail_description
    assert set(repo_mapping.mapping[0].target) == {'pesid2', 'pesid3'}, fail_description

    # 2. Verify that only repositories valid for the current IPU are produced
    pesid_repos = repo_mapping.repositories
    fail_description = 'Actor produced incorrect number of IPU-relevant pesid repos.'
    assert len(pesid_repos) == 3, fail_description

    expected_pesid_repos = [
        PESIDRepositoryEntry(
            pesid='pesid1',
            major_version='7',
            repoid='some-rhel-7-repoid',
            arch='x86_64',
            repo_type='rpm',
            channel='eus',
            rhui=''
        ),
        PESIDRepositoryEntry(
            pesid='pesid2',
            major_version='8',
            repoid='some-rhel-8-repoid1',
            arch='x86_64',
            repo_type='rpm',
            channel='eus',
            rhui=''
        ),
        PESIDRepositoryEntry(
            pesid='pesid3',
            major_version='8',
            repoid='some-rhel-8-repoid2',
            arch='x86_64',
            repo_type='rpm',
            channel='eus',
            rhui=''
        ),
    ]

    fail_description = 'Expected pesid repo is not present in the deserialization output.'
    for expected_pesid_repo in expected_pesid_repos:
        assert expected_pesid_repo in pesid_repos, fail_description


def test_scan_repositories_with_missing_data(monkeypatch):
    """
    Tests whether the scanning process fails gracefully when no data are read.
    """
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='7.9', dst_ver='8.4'))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(repositoriesmapping, 'read_or_fetch', lambda dummy: '')

    with pytest.raises(StopActorExecutionError) as missing_data_error:
        repositoriesmapping.scan_repositories()
    assert 'does not contain a valid JSON object' in str(missing_data_error)


def test_scan_repositories_with_empty_data(monkeypatch):
    """
    Tests whether the scanning process fails gracefully when empty json data received.
    """

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='7.9', dst_ver='8.4'))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    with pytest.raises(StopActorExecutionError) as empty_data_error:
        repositoriesmapping.scan_repositories(lambda dummy: {})
    assert 'the JSON is missing a required field' in str(empty_data_error)


@pytest.mark.parametrize('version_format', ('0.0.0', '1.0.1', '1.1.0', '2.0.0'))
def test_scan_repositories_with_bad_json_data_version(monkeypatch, version_format):
    """
    Tests whether the json data is checked for the version field and error is raised if the version
    does not match the latest one.
    """

    json_data = {
        'datetime': '202107141655Z',
        'version_format': version_format,
        'mapping': [],
        'repositories': []
    }

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='7.9', dst_ver='8.4'))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    with pytest.raises(StopActorExecutionError) as bad_version_error:
        repositoriesmapping.scan_repositories(lambda dummy: json_data)

    assert 'mapping file is invalid' in str(bad_version_error)


def test_scan_repositories_with_mapping_to_pesid_without_repos(monkeypatch):
    """
    Tests that the loading of repositories mapping recognizes when there is a mapping with target pesid that does
    not have any repositories and inhibits the upgrade.
    """
    json_data = {
        'datetime': '202107141655Z',
        'version_format': repositoriesmapping.RepoMapData.VERSION_FORMAT,
        'mapping': [
            {
                'source_major_version': '7',
                'target_major_version': '8',
                'entries':  [
                    {
                        'source': 'source_pesid',
                        'target': ['nonexisting_pesid']
                    }
                ]
            }
        ],
        'repositories': [
            {
                'pesid': 'source_pesid',
                'entries': [
                    {
                        'major_version': '7',
                        'repoid': 'some-rhel-7-repo',
                        'arch': 'x86_64',
                        'repo_type': 'rpm',
                        'channel': 'eus'
                    }
                ]
            }
        ]
    }

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='7.9', dst_ver='8.4'))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    with pytest.raises(StopActorExecutionError) as error_info:
        repositoriesmapping.scan_repositories(lambda dummy: json_data)

    assert 'pesid is not related to any repository' in error_info.value.message


def test_scan_repositories_with_repo_entry_missing_required_fields(monkeypatch):
    """
    Tests whether deserialization of pesid repo entries missing some of the required fields
    is handled internally and StopActorExecutionError is propagated to the user.
    """

    json_data = {
        'datetime': '202107141655Z',
        'version_format': repositoriesmapping.RepoMapData.VERSION_FORMAT,
        'mapping': [
            {
                'source_major_version': '7',
                'target_major_version': '8',
                'entries':  [
                    {
                        'source': 'source_pesid',
                        'target': ['target_pesid']
                    }
                ]
            }
        ],
        'repositories': [
            {
                'pesid': 'source_pesid',
                'entries': [
                    {
                        'major_version': '7',
                        'repoid': 'some-rhel-9-repo1',
                        'arch': 'x86_64',
                    }
                ]
            },
            {
                'pesid': 'target_pesid',
                'entries': [
                    {
                        'major_version': '7',
                        'repoid': 'some-rhel-9-repo1',
                        'arch': 'x86_64',
                    }
                ]
            }
        ]
    }

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='7.9', dst_ver='8.4'))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    with pytest.raises(StopActorExecutionError) as error_info:
        repositoriesmapping.scan_repositories(lambda dummy: json_data)

    assert 'the JSON is missing a required field' in error_info.value.message


def test_scan_repositories_with_repo_entry_mapping_target_not_a_list(monkeypatch):
    """
    Tests whether deserialization of a mapping entry that has its target field set to a string
    is handled internally and StopActorExecutionError is propagated to the user.
    """

    json_data = {
        'datetime': '202107141655Z',
        'version_format': repositoriesmapping.RepoMapData.VERSION_FORMAT,
        'mapping': [
            {
                'source_major_version': '7',
                'target_major_version': '8',
                'entries':  [
                    {
                        'source': 'source_pesid',
                        'target': 'target_pesid'
                    }
                ]
            }
        ],
        'repositories': [
            {
                'pesid': 'source_pesid',
                'entries': [
                    {
                        'major_version': '7',
                        'repoid': 'some-rhel-9-repo1',
                        'arch': 'x86_64',
                    }
                ]
            },
            {
                'pesid': 'target_pesid',
                'entries': [
                    {
                        'major_version': '7',
                        'repoid': 'some-rhel-9-repo1',
                        'arch': 'x86_64',
                    }
                ]
            }
        ]
    }

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='7.9', dst_ver='8.4'))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    with pytest.raises(StopActorExecutionError) as error_info:
        repositoriesmapping.scan_repositories(lambda dummy: json_data)

    assert 'repository mapping file is invalid' in error_info.value.message
