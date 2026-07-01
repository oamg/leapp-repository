import pytest

from leapp.libraries.actor import removerockylogossymlinks
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import DNFWorkaround


def test_rocky_produces_workaround(monkeypatch):
    actor_mock = CurrentActorMocked(src_distro='rocky', dst_distro='rhel')
    monkeypatch.setattr(api, 'current_actor', actor_mock)
    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)

    removerockylogossymlinks.process()

    assert produce_mock.called == 1
    workaround = produce_mock.model_instances[0]
    assert isinstance(workaround, DNFWorkaround)
    assert workaround.display_name == 'Rocky Linux compatibility symlinks fix'


@pytest.mark.parametrize('distro', ['rhel', 'centos', 'almalinux'])
def test_non_rocky_skips(monkeypatch, distro):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_distro=distro, dst_distro='rhel'))
    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)

    removerockylogossymlinks.process()

    assert produce_mock.called == 0
