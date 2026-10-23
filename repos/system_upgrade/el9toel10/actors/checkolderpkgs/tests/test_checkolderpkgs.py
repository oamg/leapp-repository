import pytest

from leapp import reporting
from leapp.libraries.actor import checkolderpkgs
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import InstalledRPM, RPM
from leapp.utils.report import is_inhibitor


@pytest.mark.parametrize(
    'release_string,current_version,expected',
    [
        # Older releases - should return True
        ('1.el7', '9', True),
        ('2.el8', '9', True),
        ('1.el6', '9', True),
        ('5.el7_9', '9', True),
        ('1.el8_10', '9', True),
        # Current release - should return False
        ('1.el9', '9', False),
        ('2.el9_4', '9', False),
        ('3.el9.x86_64', '9', False),
        # Future releases - should return False (not older)
        ('1.el10', '9', False),
        ('1.el11', '9', False),
        # Edge cases
        ('', '9', False),
        ('1.fc38', '9', False),  # Fedora, not RHEL
        ('1.module+el9', '9', False),  # module stream
        ('custom_build', '9', False),  # no .el tag
        # RHEL 8 source checking RHEL 7 packages
        ('1.el7', '8', True),
        ('1.el6', '8', True),
        ('1.el8', '8', False),
    ]
)
def test_is_older_release(release_string, current_version, expected):
    """
    Test _is_older_release correctly identifies packages from older releases.
    """
    result = checkolderpkgs._is_older_release(release_string, current_version)
    assert result == expected, (
        'Failed for release={}, version={}: expected {}, got {}'
        .format(release_string, current_version, expected, result)
    )


def test_no_older_packages_no_report(monkeypatch):
    """
    Test that no report is generated when all packages are from current release.
    """
    logger = logger_mocked()
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[
        InstalledRPM(items=[
            RPM(
                name='current-package-1',
                version='1.0',
                release='1.el9',
                arch='x86_64',
                epoch='0',
                packager='',
                pgpsig=''
            ),
            RPM(
                name='current-package-2',
                version='2.5',
                release='3.el9_4',
                arch='x86_64',
                epoch='0',
                packager='',
                pgpsig=''
            ),
        ])
    ]))
    # Mock get_source_major_version to return '9'
    monkeypatch.setattr(
        'leapp.libraries.actor.checkolderpkgs.get_source_major_version',
        lambda: '9'
    )

    checkolderpkgs.process()

    assert 'No packages from older RHEL releases detected.' in logger.dbgmsg
    assert not reporting.create_report.called


def test_older_packages_creates_inhibitor(monkeypatch):
    """
    Test that an inhibitor report is created when older packages are detected.
    """
    logger = logger_mocked()
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[
        InstalledRPM(items=[
            RPM(
                name='old-package-el7',
                version='1.0',
                release='1.el7',
                arch='x86_64',
                epoch='0',
                packager='',
                pgpsig=''
            ),
            RPM(
                name='old-package-el8',
                version='2.0',
                release='2.el8_5',
                arch='x86_64',
                epoch='0',
                packager='',
                pgpsig=''
            ),
            RPM(
                name='current-package',
                version='3.0',
                release='1.el9',
                arch='x86_64',
                epoch='0',
                packager='',
                pgpsig=''
            ),
        ])
    ]))
    monkeypatch.setattr(
        'leapp.libraries.actor.checkolderpkgs.get_source_major_version',
        lambda: '9'
    )

    checkolderpkgs.process()

    assert reporting.create_report.called
    assert len(reporting.create_report.reports) == 1

    report = reporting.create_report.reports[0]
    assert report['title'] == 'Packages from different RHEL releases detected'
    assert 'old-package-el7' in report['summary']
    assert 'old-package-el8' in report['summary']
    assert '2 package(s)' in report['summary']
    assert report['severity'] == reporting.Severity.HIGH
    assert is_inhibitor(report)


def test_multiple_installed_rpm_messages(monkeypatch):
    """
    Test handling of multiple InstalledRPM messages.
    """
    logger = logger_mocked()
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[
        InstalledRPM(items=[
            RPM(
                name='old-pkg-1',
                version='1.0',
                release='1.el7',
                arch='x86_64',
                epoch='0',
                packager='',
                pgpsig=''
            ),
        ]),
        InstalledRPM(items=[
            RPM(
                name='old-pkg-2',
                version='1.0',
                release='1.el8',
                arch='x86_64',
                epoch='0',
                packager='',
                pgpsig=''
            ),
        ]),
    ]))
    monkeypatch.setattr(
        'leapp.libraries.actor.checkolderpkgs.get_source_major_version',
        lambda: '9'
    )

    checkolderpkgs.process()

    assert reporting.create_report.called
    report = reporting.create_report.reports[0]
    assert 'old-pkg-1' in report['summary']
    assert 'old-pkg-2' in report['summary']


def test_many_older_packages_truncates_list(monkeypatch):
    """
    Test that report truncates package list when there are many packages.
    """
    logger = logger_mocked()
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger)

    # Create 25 packages from older releases
    old_packages = [
        RPM(
            name='old-package-{}'.format(i),
            version='1.0',
            release='1.el7',
            arch='x86_64',
            epoch='0',
            packager='',
            pgpsig=''
        )
        for i in range(25)
    ]

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[
        InstalledRPM(items=old_packages)
    ]))
    monkeypatch.setattr(
        'leapp.libraries.actor.checkolderpkgs.get_source_major_version',
        lambda: '9'
    )

    checkolderpkgs.process()

    assert reporting.create_report.called
    report = reporting.create_report.reports[0]
    assert '25 package(s)' in report['summary']
    # Should show message about additional packages
    assert 'and 5 more packages' in report['summary']


def test_package_with_no_release_field(monkeypatch):
    """
    Test handling of packages with empty or None release field.
    """
    logger = logger_mocked()
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[
        InstalledRPM(items=[
            RPM(
                name='no-release-pkg',
                version='1.0',
                release='',
                arch='x86_64',
                epoch='0',
                packager='',
                pgpsig=''
            ),
        ])
    ]))
    monkeypatch.setattr(
        'leapp.libraries.actor.checkolderpkgs.get_source_major_version',
        lambda: '9'
    )

    checkolderpkgs.process()

    assert not reporting.create_report.called
    assert 'No packages from older RHEL releases detected.' in logger.dbgmsg


def test_remediation_hint_in_report(monkeypatch):
    """
    Test that the inhibitor report contains proper remediation guidance.
    """
    logger = logger_mocked()
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[
        InstalledRPM(items=[
            RPM(
                name='old-pkg',
                version='1.0',
                release='1.el7',
                arch='x86_64',
                epoch='0',
                packager='',
                pgpsig=''
            ),
        ])
    ]))
    monkeypatch.setattr(
        'leapp.libraries.actor.checkolderpkgs.get_source_major_version',
        lambda: '9'
    )

    checkolderpkgs.process()

    assert reporting.create_report.called
    report = reporting.create_report.reports[0]

    # Check that remediation contains key steps
    remediation = report.get('detail', {}).get('remediations', [{}])[0].get('context', '')
    assert 'yum remove' in remediation
    assert 'Red Hat Support' in remediation
