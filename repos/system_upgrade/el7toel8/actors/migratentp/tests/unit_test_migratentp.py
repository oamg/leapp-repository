from leapp import reporting
from leapp.libraries.actor import migratentp
from leapp.libraries.common.testutils import create_report_mocked


class extract_tgz64_mocked(object):
    def __init__(self):
        self.called = 0
        self.s = None

    def __call__(self, s):
        self.called += 1
        self.s = s


class enable_service_mocked(object):
    def __init__(self):
        self.called = 0
        self.names = []

    def __call__(self, name):
        self.called += 1
        self.names.append(name)


class write_file_mocked(object):
    def __init__(self):
        self.called = 0
        self.name = None
        self.content = None

    def __call__(self, name, content):
        self.called += 1
        self.name = name
        self.content = content


class ntp2chrony_mocked(object):
    def __init__(self, lines):
        self.called = 0
        self.ignored_lines = lines
        self.args = None

    def __call__(self, *args):
        self.called += 1
        self.args = args
        return True, self.ignored_lines * ['a line']


def test_migration(monkeypatch):
    for ntp_services, chrony_services, ignored_lines in [
                ([], [], 0),
                (['ntpd'], ['chronyd'], 0),
                (['ntpdate'], ['chronyd'], 1),
                (['ntp-wait'], ['chrony-wait'], 0),
                (['ntpd', 'ntpdate', 'ntp-wait'], ['chronyd', 'chronyd', 'chrony-wait'], 1),
            ]:
        monkeypatch.setattr(migratentp, 'extract_tgz64', extract_tgz64_mocked())
        monkeypatch.setattr(migratentp, 'enable_service', enable_service_mocked())
        monkeypatch.setattr(migratentp, 'write_file', write_file_mocked())
        monkeypatch.setattr(migratentp, 'ntp2chrony', ntp2chrony_mocked(ignored_lines))

        migratentp.migrate_ntp(ntp_services, 'abcdef')

        if ntp_services:
            assert migratentp.extract_tgz64.called == 1
            assert migratentp.extract_tgz64.s == 'abcdef'
            assert migratentp.enable_service.called == len(chrony_services)
            assert migratentp.enable_service.names == chrony_services
            assert migratentp.write_file.called == (0 if 'ntpd' in ntp_services else 1)
            if migratentp.write_file.called:
                assert migratentp.write_file.name == '/etc/ntp.conf.nosources'
                assert 'without ntp configuration' in migratentp.write_file.content
            assert migratentp.ntp2chrony.called == 1
            assert migratentp.ntp2chrony.args == (
                    '/',
                    '/etc/ntp.conf' if 'ntpd' in ntp_services else '/etc/ntp.conf.nosources',
                    '/etc/ntp/step-tickers' if 'ntpdate' in ntp_services else '')
        else:
            assert migratentp.extract_tgz64.called == 0
            assert migratentp.enable_service.called == 0
            assert migratentp.write_file.called == 0
            assert migratentp.ntp2chrony.called == 0
