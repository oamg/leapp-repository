import os

import pytest

from leapp.libraries.actor import applycustomdnfconf


@pytest.mark.parametrize(
    "exists,should_move",
    [(False, False), (True, True)],
)
def test_copy_correct_dnf_conf(monkeypatch, exists, should_move):
    monkeypatch.setattr(os.path, "exists", lambda _: exists)

    run_called = [False]

    def mocked_run(_):
        run_called[0] = True

    monkeypatch.setattr(applycustomdnfconf, 'run', mocked_run)

    applycustomdnfconf.process()
    assert run_called[0] == should_move
