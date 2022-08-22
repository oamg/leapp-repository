import base64
import io
import os
import re
import tarfile
import tempfile

from leapp import reporting
from leapp.libraries.actor import checkntp
from leapp.libraries.common.testutils import create_report_mocked


def test_nomigration(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkntp, 'check_service', lambda _: False)
    monkeypatch.setattr(checkntp, 'is_file', lambda _: False)
    monkeypatch.setattr(checkntp, 'get_tgz64', lambda _: '')

    checkntp.check_ntp(set(['chrony', 'linuxptp', 'xterm']))

    assert reporting.create_report.called == 0


def test_migration(monkeypatch):
    for packages, services, migrate in [
                (['ntp'], ['ntpd'], ['ntpd']),
                (['ntp', 'ntpdate'], ['ntpd'], ['ntpd']),
                (['ntpdate'], ['ntpdate'], ['ntpdate']),
                (['ntp', 'ntpdate'], ['ntpdate'], ['ntpdate']),
                (['ntp', 'ntpdate'], ['ntpd', 'ntpdate'], ['ntpd', 'ntpdate']),
                (['ntp', 'ntpdate', 'ntp-perl'], ['ntpd', 'ntpdate'], ['ntpd', 'ntpdate']),
                (['ntp', 'ntpdate'], ['ntpd', 'ntpdate', 'ntp-wait'], ['ntpd', 'ntpdate']),
                (['ntp', 'ntpdate', 'ntp-perl'], ['ntpd', 'ntpdate', 'ntp-wait'], ['ntpd', 'ntpdate', 'ntp-wait']),
            ]:
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
        monkeypatch.setattr(checkntp, 'check_service', lambda service: service[:-8] in services)
        monkeypatch.setattr(checkntp, 'is_file', lambda _: True)
        monkeypatch.setattr(checkntp, 'get_tgz64', lambda _: '')

        decision = checkntp.check_ntp(set(packages))

        assert reporting.create_report.called == 1
        assert 'configuration will be migrated' in reporting.create_report.report_fields['title']
        for service in ['ntpd', 'ntpdate']:
            migrated = re.search(r'\b{}\b'.format(service),
                                 reporting.create_report.report_fields['title']) is not None
            assert migrated == (service in migrate)

        assert decision.migrate_services == migrate


def test_tgz64(monkeypatch):
    f, name = tempfile.mkstemp()
    os.close(f)
    tgz64 = checkntp.get_tgz64([name])

    stream = io.BytesIO(base64.b64decode(tgz64))
    tar = tarfile.open(fileobj=stream, mode='r:gz')
    names = tar.getnames()

    tar.close()
    os.unlink(name)

    assert names == [name.lstrip('/')]
