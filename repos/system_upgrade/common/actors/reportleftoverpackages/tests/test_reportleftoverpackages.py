from leapp import reporting
from leapp.libraries.actor import reportleftoverpackages
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import LeftoverPackages, RemovedPackages, RPM


def test_no_leftover_and_no_removed_packages(monkeypatch):
    removed_packages = RemovedPackages()
    leftover_packages = LeftoverPackages()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[leftover_packages, removed_packages]))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    reportleftoverpackages.process()

    assert reporting.create_report.called == 0
    assert api.current_logger.infomsg == ['No leftover packages, skipping...']


def test_no_removed_packages_leftover_present(monkeypatch):
    removed_packages = RemovedPackages()
    leftover_packages = LeftoverPackages(items=[RPM(name='rpm', version='1.0', release='1.el7', epoch='0',
                                                    packager='foo', arch='noarch', pgpsig='SIG')])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[leftover_packages, removed_packages]))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    reportleftoverpackages.process()

    assert reporting.create_report.called == 1
    assert 'Some RHEL packages have not been upgraded' in reporting.create_report.report_fields['title']
    assert 'Following RHEL packages have not been upgraded' in reporting.create_report.report_fields['summary']
    summary = 'Please remove these packages to keep your system in supported state.'
    assert summary in reporting.create_report.report_fields['summary']
    assert 'rpm-1.0-1.el7' in reporting.create_report.report_fields['summary']


def test_removed_packages(monkeypatch):
    leftover_packages = LeftoverPackages()
    removed_packages = RemovedPackages(items=[RPM(name='rpm', version='1.0', release='1.el7', epoch='0',
                                                  packager='foo', arch='noarch', pgpsig='SIG')])

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[removed_packages, leftover_packages]))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    reportleftoverpackages.process()

    assert reporting.create_report.called == 1
    assert 'Leftover RHEL packages have been removed' in reporting.create_report.report_fields['title']
    assert 'Following packages have been removed' in reporting.create_report.report_fields['summary']
    assert 'rpm-1.0-1.el7' in reporting.create_report.report_fields['summary']
