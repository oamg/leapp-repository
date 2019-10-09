from collections import namedtuple

import pytest

from leapp.exceptions import StopActorExecution
from leapp.libraries.actor.library import scan_repositories
from leapp import reporting
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import produce_mocked, create_report_mocked
from leapp.libraries.stdlib import api
from leapp.models import RepositoriesMap, RepositoryMap


class CurrentActorMocked(object):
    def __init__(self, arch):
        self.configuration = namedtuple('configuration', ['architecture'])(arch)

    def __call__(self):
        return self


def test_scan_valid_file(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_X86_64))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    scan_repositories('files/tests/sample01.csv')

    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1
    assert isinstance(api.produce.model_instances[0], RepositoriesMap)
    assert len(api.produce.model_instances[0].repositories) == 4
    assert isinstance(api.produce.model_instances[0].repositories[0], RepositoryMap)
    assert api.produce.model_instances[0].repositories[0].from_repoid == 'FromRepo01'
    assert api.produce.model_instances[0].repositories[0].repo_type == 'rpm'
    assert isinstance(api.produce.model_instances[0].repositories[3], RepositoryMap)
    assert api.produce.model_instances[0].repositories[3].to_repoid == 'ToRepo04'
    assert api.produce.model_instances[0].repositories[2].to_pes_repo == 'ToName03'
    assert api.produce.model_instances[0].repositories[3].arch == architecture.ARCH_X86_64


def test_repository_mapping_file_not_found(monkeypatch):
    def file_not_exists(_filepath):
        return False
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_X86_64))
    monkeypatch.setattr('os.path.isfile', file_not_exists)
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    with pytest.raises(StopActorExecution):
        scan_repositories('/etc/leapp/files/repomap.csv')
    assert reporting.create_report.called == 1
    assert 'inhibitor' in reporting.create_report.report_fields['flags']
    assert 'Repositories map file not found' in reporting.create_report.report_fields['title']


def test_scan_empty_file(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_X86_64))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    with pytest.raises(StopActorExecution):
        scan_repositories('files/tests/sample02.csv')
    assert reporting.create_report.called == 1
    assert 'inhibitor' in reporting.create_report.report_fields['flags']
    assert 'Repositories map file is invalid' in reporting.create_report.report_fields['title']


def test_scan_invalid_file_txt(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_X86_64))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    with pytest.raises(StopActorExecution):
        scan_repositories('files/tests/sample03.csv')
    assert reporting.create_report.called == 1
    assert 'inhibitor' in reporting.create_report.report_fields['flags']
    assert 'Repositories map file is invalid' in reporting.create_report.report_fields['title']


def test_scan_invalid_file_csv(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_PPC64LE))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    with pytest.raises(StopActorExecution):
        scan_repositories('files/tests/sample04.csv')
    assert reporting.create_report.called == 1
    assert 'inhibitor' in reporting.create_report.report_fields['flags']
    assert 'Repositories map file is invalid' in reporting.create_report.report_fields['title']
