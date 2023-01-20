import os

import pytest

from leapp.libraries.actor import removeupgradeartifacts


@pytest.mark.parametrize(('exists', 'should_remove'), [
    (True, True),
    (False, False),
])
def test_remove_upgrade_artifacts(monkeypatch, exists, should_remove):

    called = [False]

    def mocked_run(cmd, *args, **kwargs):
        assert cmd[0] == 'rm'
        assert cmd[1] == '-rf'
        assert cmd[2] == removeupgradeartifacts.UPGRADE_ARTIFACTS_DIR
        called[0] = True
        return {'exit_code': 0, 'stdout': '', 'stderr': ''}

    monkeypatch.setattr(os.path, 'exists', lambda _: exists)
    monkeypatch.setattr(removeupgradeartifacts, 'run', mocked_run)

    removeupgradeartifacts.process()

    assert called[0] == should_remove
