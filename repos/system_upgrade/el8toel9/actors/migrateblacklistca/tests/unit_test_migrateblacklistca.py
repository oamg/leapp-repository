import os

from leapp.libraries.actor import migrateblacklistca
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api


class MockedGetFiles():
    def __init__(self):
        self.called = 0

    def __call__(self):
        self.called += 1
        return []


def test_no_dirs_exist(monkeypatch):
    mocked_files = MockedGetFiles()
    monkeypatch.setattr(os.path, 'exists', lambda dummy: False)
    monkeypatch.setattr(migrateblacklistca, '_get_files', mocked_files)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    # this is bad mock, but we want to be sure that update-ca-trust is not
    # called on the testing machine
    monkeypatch.setattr(migrateblacklistca, 'run', lambda dummy: dummy)
    assert not mocked_files.called
