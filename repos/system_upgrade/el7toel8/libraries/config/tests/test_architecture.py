import pytest

from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api


def test_matches_architecture_pass(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=architecture.ARCH_ACCEPTED[0]))
    assert architecture.matches_architecture(*architecture.ARCH_ACCEPTED)


def test_matches_architecture_fail(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=architecture.ARCH_ACCEPTED[0]))
    assert not architecture.matches_architecture()
    assert not architecture.matches_architecture(*architecture.ARCH_ACCEPTED[1:])


def test_matches_architecture_wrong_args():
    with pytest.raises(TypeError):
        architecture.matches_architecture('aarch64', 1)
