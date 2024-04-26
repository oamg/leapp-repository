import glob

from leapp.models import SatelliteFacts, SatellitePostgresqlFacts, SystemdServicesTasks


def test_disable_httpd(monkeypatch, current_actor_context):
    def mock_glob():
        orig_glob = glob.glob

        def mocked_glob(pathname):
            if pathname == '/etc/systemd/system/multi-user.target.wants/httpd.service':
                return [pathname]
            return orig_glob(pathname)

        return mocked_glob

    monkeypatch.setattr('glob.glob', mock_glob())

    current_actor_context.feed(SatelliteFacts(has_foreman=True,
                                              postgresql=SatellitePostgresqlFacts(local_postgresql=False)))
    current_actor_context.run()

    message = current_actor_context.consume(SystemdServicesTasks)[0]
    assert 'httpd.service' in message.to_disable
