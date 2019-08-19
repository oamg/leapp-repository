from leapp.libraries.actor import library
from leapp.libraries.common.testutils import create_report_mocked
from leapp import reporting


def is_executable_only_gnome(path):
    return path == "/usr/bin/gnome-session"


def is_executable_only_kde(path):
    return path == "/usr/bin/startkde"


def check_app_in_use_mocked(app):
    #  Only one app in use
    return app == "okular"


def get_xsession_gnome(path):
    return "gnome"


def get_xsession_kde(path):
    return "plasma"


def test_no_desktop(monkeypatch):
    """
    Scenario: There is no desktop.
    Expected behavior: No report
    """
    #  Desktop presence is found by trying to execute gnome-session or startkde
    monkeypatch.setattr(library, "is_executable", lambda x: False)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    library.check_kde_gnome()

    assert reporting.create_report.called == 0


def test_only_gnome_without_apps(monkeypatch):
    """
    Scenario: KDE and KDE apps are NOT installed
    Expected behavior: No report
    """

    monkeypatch.setattr(library, "is_executable", is_executable_only_gnome)
    monkeypatch.setattr(library, "is_installed", lambda x: False)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    library.check_kde_gnome()

    assert reporting.create_report.called == 0


def test_only_gnome_without_active_apps(monkeypatch):
    """
    Scenatio: no KDE desktop is installed, but there are some KDE apps, which are not active
    Expected behavior: No report (unused app is not considered to be important)

    """
    monkeypatch.setattr(library, "is_executable", is_executable_only_gnome)
    monkeypatch.setattr(library, "is_installed", lambda x: True)
    monkeypatch.setattr(library, "check_app_in_use", lambda x: False)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    library.check_kde_gnome()

    assert reporting.create_report.called == 0


def test_only_gnome_with_active_apps(monkeypatch):
    """
    Scenatio: no KDE desktop is installed, but there are some KDE apps, which are actively used
    Expected behavior: Report is made (severity = MEDIUM)

    """
    monkeypatch.setattr(library, "is_executable", is_executable_only_gnome)
    monkeypatch.setattr(library, "is_installed", lambda x: True)
    monkeypatch.setattr(library, "check_app_in_use", check_app_in_use_mocked)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    library.check_kde_gnome()

    assert reporting.create_report.called == 1
    #  Do not even touch the string! It is ugly, but because of max line lenght it has to
    #  be written on two lines.
    assert reporting.create_report.report_fields["title"] == "Upgrade can be\
 performed, but KDE apps will be uninstalled."


def test_only_kde(monkeypatch):
    """
    Scenario: There is only KDE installed.
    Expected behavior: Report is generated with HIGH severity and inhibitor tag.
    """
    monkeypatch.setattr(library, "is_executable", is_executable_only_kde)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    library.check_kde_gnome()

    assert reporting.create_report.called == 1
    assert "inhibitor" in reporting.create_report.report_fields["flags"]


def test_both_gnome_main_without_active_apps(monkeypatch):
    """
    Scenario: There are both KDE and GNOME installed, GNOME is the main desktop
    and there are no KDE apps
    Expected behavior: No report is generated.
    """
    monkeypatch.setattr(library, "is_executable", lambda x: True)
    monkeypatch.setattr(library, "is_installed", lambda x: False)
    monkeypatch.setattr(library, "get_xsession", get_xsession_gnome)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    library.check_kde_gnome()

    assert reporting.create_report.called == 0


def test_both_gnome_main_with_active_apps(monkeypatch):
    """
    Scenario: There are both KDE and GNOME installed, GNOME is the main desktop
    and there are some KDE apps
    Expected behavior: Report is generated about deleting KDE apps
    """
    monkeypatch.setattr(library, "is_executable", lambda x: True)
    monkeypatch.setattr(library, "is_installed", lambda x: True)
    monkeypatch.setattr(library, "get_xsession", get_xsession_gnome)
    monkeypatch.setattr(library, "check_app_in_use", check_app_in_use_mocked)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    library.check_kde_gnome()

    assert reporting.create_report.called == 1
    #  Do not even touch the string! It is ugly, but because of max line lenght it has to
    #  be written on two lines.
    assert reporting.create_report.report_fields["title"] == "Upgrade can be\
 performed, but KDE apps will be uninstalled."


def test_both_kde_main_without_active_apps(monkeypatch):
    """
    Scenario: There are both KDE and GNOME installed, KDE is the main desktop
    and there are no KDE apps
    Expected behavior: There is a report generated.
    """
    monkeypatch.setattr(library, "is_executable", lambda x: True)
    monkeypatch.setattr(library, "is_installed", lambda x: False)
    monkeypatch.setattr(library, "get_xsession", get_xsession_kde)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    library.check_kde_gnome()

    assert reporting.create_report.called == 1
    assert reporting.create_report.report_fields["title"] == "Upgrade can be\
 performed, but KDE will be uninstalled."


def test_both_kde_main_with_active_apps(monkeypatch):
    """
    Scenario: There are both KDE and GNOME installed, KDE is the main desktop
    and there are some KDE apps
    Expected behavior: Two reports are generated: one about KDE and one about KDE apps.
    """
    monkeypatch.setattr(library, "is_executable", lambda x: True)
    monkeypatch.setattr(library, "is_installed", lambda x: True)
    monkeypatch.setattr(library, "get_xsession", get_xsession_kde)
    monkeypatch.setattr(library, "check_app_in_use", check_app_in_use_mocked)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    library.check_kde_gnome()

    assert reporting.create_report.called == 2
