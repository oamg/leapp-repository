from leapp import reporting
from leapp.libraries.actor.satellite_upgrade_check import satellite_upgrade_check
from leapp.libraries.common.testutils import create_report_mocked
from leapp.models import SatelliteFacts, SatellitePostgresqlFacts


def test_old_data(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    satellite_upgrade_check(SatelliteFacts(has_foreman=True,
                            postgresql=SatellitePostgresqlFacts(local_postgresql=True, old_var_lib_pgsql_data=True)))

    assert reporting.create_report.called == 2

    expected_title = 'Old PostgreSQL data found in /var/lib/pgsql/data'
    assert next((report for report in reporting.create_report.reports if report.get('title') == expected_title), None)

    expected_title = 'Satellite PostgreSQL data migration'
    assert next((report for report in reporting.create_report.reports if report.get('title') == expected_title), None)


def test_no_old_data(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    satellite_upgrade_check(SatelliteFacts(has_foreman=True,
                            postgresql=SatellitePostgresqlFacts(local_postgresql=True, old_var_lib_pgsql_data=False)))

    assert reporting.create_report.called == 1

    expected_title = 'Satellite PostgreSQL data migration'

    assert expected_title == reporting.create_report.report_fields['title']


def test_same_disk(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    satellite_upgrade_check(SatelliteFacts(has_foreman=True,
                            postgresql=SatellitePostgresqlFacts(local_postgresql=True, same_partition=True)))

    assert reporting.create_report.called == 1

    expected_title = 'Satellite PostgreSQL data migration'
    expected_summary = 'Your PostgreSQL data will be automatically migrated.'
    expected_reindex = 'all databases will require a REINDEX'

    assert expected_title == reporting.create_report.report_fields['title']
    assert expected_summary in reporting.create_report.report_fields['summary']
    assert expected_reindex in reporting.create_report.report_fields['summary']


def test_different_disk_sufficient_storage(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    satellite_upgrade_check(SatelliteFacts(has_foreman=True,
                            postgresql=SatellitePostgresqlFacts(local_postgresql=True, same_partition=False,
                                                                space_required=5, space_available=10)))

    assert reporting.create_report.called == 1

    expected_title = 'Satellite PostgreSQL data migration'
    expected_summary = 'You currently have enough free storage to move the data'
    expected_reindex = 'all databases will require a REINDEX'

    assert expected_title == reporting.create_report.report_fields['title']
    assert expected_summary in reporting.create_report.report_fields['summary']
    assert expected_reindex in reporting.create_report.report_fields['summary']


def test_different_disk_insufficient_storage(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    satellite_upgrade_check(SatelliteFacts(has_foreman=True,
                            postgresql=SatellitePostgresqlFacts(local_postgresql=True, same_partition=False,
                                                                space_required=10, space_available=5)))

    assert reporting.create_report.called == 1

    expected_title = 'Satellite PostgreSQL data migration'
    expected_summary = "You currently don't have enough free storage to move the data"

    assert expected_title == reporting.create_report.report_fields['title']
    assert expected_summary in reporting.create_report.report_fields['summary']
