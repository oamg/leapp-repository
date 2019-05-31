from leapp.libraries.actor import library
from leapp.libraries.common import reporting


class report_generic_mocked(object):
    def __init__(self):
        self.called = 0

    def __call__(self, **report_fields):
        self.called += 1
        self.report_fields = report_fields


class extract_tgz64_mocked(object):
    def __init__(self):
        self.called = 0

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

    def __call__(self, name, content):
        self.called += 1
        self.name = name
        self.content = content


class ntp2chrony_mocked(object):
    def __init__(self, lines):
        self.called = 0
        self.ignored_lines = lines

    def __call__(self, *args):
        self.called += 1
        self.args = args
        return self.ignored_lines * ['a line']


def test_migration(monkeypatch):
    for ntp_services, chrony_services, ignored_lines in [
                ([], [], 0),
                (['ntpd'], ['chronyd'], 0),
                (['ntpdate'], ['chronyd'], 1),
                (['ntp-wait'], ['chrony-wait'], 0),
                (['ntpd', 'ntpdate', 'ntp-wait'], ['chronyd', 'chronyd', 'chrony-wait'], 1),
            ]:
        monkeypatch.setattr(reporting, 'report_generic', report_generic_mocked())
        monkeypatch.setattr(library, 'extract_tgz64', extract_tgz64_mocked())
        monkeypatch.setattr(library, 'enable_service', enable_service_mocked())
        monkeypatch.setattr(library, 'write_file', write_file_mocked())
        monkeypatch.setattr(library, 'ntp2chrony', ntp2chrony_mocked(ignored_lines))

        library.migrate_ntp(ntp_services, 'abcdef')

        if len(ntp_services) > 0:
            assert reporting.report_generic.called == 1
            if ignored_lines > 0:
                assert 'configuration partially migrated to chrony' in \
                        reporting.report_generic.report_fields['title']
            else:
                assert 'configuration migrated to chrony' in \
                        reporting.report_generic.report_fields['title']

            assert library.extract_tgz64.called == 1
            assert library.extract_tgz64.s == 'abcdef'
            assert library.enable_service.called == len(chrony_services)
            assert library.enable_service.names == chrony_services
            assert library.write_file.called == (0 if 'ntpd' in ntp_services else 1)
            if library.write_file.called:
                assert library.write_file.name == '/etc/ntp.conf.nosources'
                assert 'without ntp configuration' in library.write_file.content
            assert library.ntp2chrony.called == 1
            assert library.ntp2chrony.args == (
                    '/',
                    '/etc/ntp.conf' if 'ntpd' in ntp_services else '/etc/ntp.conf.nosources',
                    '/etc/ntp/step-tickers' if 'ntpdate' in ntp_services else '')
        else:
            assert reporting.report_generic.called == 0
            assert library.extract_tgz64.called == 0
            assert library.enable_service.called == 0
            assert library.write_file.called == 0
            assert library.ntp2chrony.called == 0
