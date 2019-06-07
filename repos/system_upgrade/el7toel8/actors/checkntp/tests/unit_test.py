import base64
import io
import os
import re
import tarfile
import tempfile

from leapp.libraries.actor import library
from leapp.libraries.common import reporting
from leapp.libraries.common.testutils import report_generic_mocked


def test_nomigration(monkeypatch):
    monkeypatch.setattr(reporting, 'report_generic', report_generic_mocked())
    monkeypatch.setattr(library, 'check_service', lambda _: False)
    monkeypatch.setattr(library, 'is_file', lambda _: False)
    monkeypatch.setattr(library, 'get_tgz64', lambda _: '')

    library.check_ntp(set(['chrony', 'linuxptp', 'xterm']))

    assert reporting.report_generic.called == 0


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
        monkeypatch.setattr(reporting, 'report_generic', report_generic_mocked())
        monkeypatch.setattr(library, 'check_service',
                                     lambda service: service[:-8] in services)
        monkeypatch.setattr(library, 'is_file', lambda _: True)
        monkeypatch.setattr(library, 'get_tgz64', lambda _: '')

        decision = library.check_ntp(set(packages))

        assert reporting.report_generic.called == 1
        assert 'configuration will be migrated' in reporting.report_generic.report_fields['title']
        for service in ['ntpd', 'ntpdate']:
            migrated = re.search(r'\b{}\b'.format(service),
                                 reporting.report_generic.report_fields['title']) is not None
            assert migrated == (service in migrate)

        assert decision.migrate_services == migrate


def test_tgz64(monkeypatch):
    f, name = tempfile.mkstemp()
    os.close(f)
    tgz64 = library.get_tgz64([name])

    stream = io.BytesIO(base64.b64decode(tgz64))
    tar = tarfile.open(fileobj=stream, mode='r:gz')
    names = tar.getnames()

    tar.close()
    os.unlink(name)

    assert names == [name.lstrip('/')]
