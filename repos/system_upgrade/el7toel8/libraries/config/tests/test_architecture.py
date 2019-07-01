import pytest

from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api


class current_actor_mocked(object):
    architecture = architecture.ARCH_ACCEPTED[0]


def test_matches_architecture_pass(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', current_actor_mocked)
    assert architecture.matches_architecture(architecture.ARCH_ACCEPTED) is True


def test_matches_architecture_fail(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', current_actor_mocked)
    assert architecture.matches_architecture([]) is False
    assert architecture.matches_architecture(architecture.ARCH_ACCEPTED[1:]) is False


def test_matches_architecture_wrong_args():
    with pytest.raises(TypeError):
        architecture.matches_architecture(['aarch64', 1])
