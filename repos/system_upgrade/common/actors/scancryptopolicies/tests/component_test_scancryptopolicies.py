import distro

from leapp.libraries.common.config import version
from leapp.models import CryptoPolicyInfo


def test_actor_execution(monkeypatch, current_actor_context):
    source_version = int(distro.major_version())
    monkeypatch.setattr(version, 'get_source_major_version', lambda: "{}".format(source_version))
    current_actor_context.run()
    if source_version > 8:
        assert current_actor_context.consume(CryptoPolicyInfo)
    else:
        assert not current_actor_context.consume(CryptoPolicyInfo)
