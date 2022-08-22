from leapp.libraries.actor import transactionworkarounds as tw
from leapp.models import RpmTransactionTasks


def test_transactionworkarounds_2rpms(monkeypatch):
    result = []
    monkeypatch.setattr(tw.os, 'listdir', lambda _: ('abc.rpm', 'def.rpm', 'random.file'),)
    monkeypatch.setattr(tw.api, 'get_folder_path', lambda _: '/FAKE/FOLDER/PATH')
    monkeypatch.setattr(tw.api, 'produce', lambda *models: result.extend(models))

    tw.process()

    assert result
    assert isinstance(result[0], RpmTransactionTasks)
    assert result[0].local_rpms
    assert result[0].local_rpms == ['/FAKE/FOLDER/PATH/abc.rpm', '/FAKE/FOLDER/PATH/def.rpm']
    assert not result[0].to_install
    assert not result[0].to_remove
    assert not result[0].to_keep


def test_transactionworkarounds_0rpms(monkeypatch):
    result = []
    monkeypatch.setattr(tw.os, 'listdir', lambda _: ('abc.not', 'def.duh', 'random.file'),)
    monkeypatch.setattr(tw.api, 'get_folder_path', lambda _: '/FAKE/FOLDER/PATH')
    monkeypatch.setattr(tw.api, 'produce', lambda *models: result.extend(models))
    tw.process()
    assert not result
