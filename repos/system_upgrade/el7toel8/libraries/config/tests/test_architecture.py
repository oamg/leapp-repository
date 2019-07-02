from collections import namedtuple

import pytest

from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api


class CurrentActorMocked(object):
    configuration = namedtuple('configuration', ['architecture'])(architecture.ARCH_ACCEPTED[0])


def test_matches_architecture_pass(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked)
    assert architecture.matches_architecture(*architecture.ARCH_ACCEPTED)


def test_matches_architecture_fail(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked)
    assert not architecture.matches_architecture()
    assert not architecture.matches_architecture(*architecture.ARCH_ACCEPTED[1:])


def test_matches_architecture_wrong_args():
    with pytest.raises(TypeError):
        architecture.matches_architecture('aarch64', 1)
