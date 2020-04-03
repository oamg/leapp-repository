import os

from leapp.snactor.fixture import current_actor_context
from leapp.models import RPM, InstalledRedHatSignedRPM
from leapp.models import IpaInfo


DEFAULT_CONF = "/etc/ipa/default.conf"
CLIENT_STATE = "/var/lib/ipa-client/sysrestore/sysrestore.state"
SERVER_STATE = "/var/lib/ipa/sysrestore/sysrestore.state"


def mock_rpm(name):
    return RPM(
        name=name,
        epoch="0",
        packager="Red Hat Inc.",
        version="4.6.0",
        release="1.el7",
        arch="x86_64",
        pgpsig="dummy",
    )


def mock_rpms(*names):
    return InstalledRedHatSignedRPM(items=[mock_rpm(name) for name in names])


def mock_os_path_isfile(overrides):
    def mocked_os_path_isfile(name):
        if name in overrides:
            return overrides[name]
        raise ValueError

    return mocked_os_path_isfile


def assert_ipa_info(infos, client, server):
    assert len(infos) == 1

    info = infos[0]
    assert info.has_client_package == client
    assert info.is_client_configured == client
    assert info.has_server_package == server
    assert info.is_server_configured == server


def test_client_configured(monkeypatch, current_actor_context):
    monkeypatch.setattr(
        "os.path.isfile",
        mock_os_path_isfile(
            {DEFAULT_CONF: True, CLIENT_STATE: True, SERVER_STATE: False}
        ),
    )

    rpms = mock_rpms("ipa-client")
    current_actor_context.feed(rpms)

    current_actor_context.run()

    infos = current_actor_context.consume(IpaInfo)
    assert_ipa_info(infos, True, False)


def test_server_configured(monkeypatch, current_actor_context):
    monkeypatch.setattr(
        "os.path.isfile",
        mock_os_path_isfile(
            {DEFAULT_CONF: True, CLIENT_STATE: True, SERVER_STATE: True}
        ),
    )

    rpms = mock_rpms("ipa-client", "ipa-server")
    current_actor_context.feed(rpms)

    current_actor_context.run()

    infos = current_actor_context.consume(IpaInfo)
    assert_ipa_info(infos, True, True)


def test_not_configured(monkeypatch, current_actor_context):
    monkeypatch.setattr(
        "os.path.isfile",
        mock_os_path_isfile(
            {DEFAULT_CONF: True, CLIENT_STATE: False, SERVER_STATE: False}
        ),
    )

    rpms = mock_rpms()
    current_actor_context.feed(rpms)
    current_actor_context.run()

    infos = current_actor_context.consume(IpaInfo)
    assert_ipa_info(infos, False, False)
