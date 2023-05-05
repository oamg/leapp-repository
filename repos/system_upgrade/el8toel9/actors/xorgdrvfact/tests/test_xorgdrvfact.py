import os

from leapp.libraries.actor import xorgdriverlib
from leapp.models import XorgDrv, XorgDrvFacts

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def _read_log_file(path):
    """
    Read a log file in text mode and return the contents as an array.

    :param path: Log file path
    """
    with open(path, 'r') as f:
        return f.read().splitlines()


def test_check_drv_and_options_qxl_driver(monkeypatch):

    def get_xorg_logs_from_journal_mocked():
        return _read_log_file(os.path.join(CUR_DIR, 'files/journalctl-xorg-qxl'))

    monkeypatch.setattr(xorgdriverlib, 'get_xorg_logs_from_journal', get_xorg_logs_from_journal_mocked)
    xorg_logs = xorgdriverlib.get_xorg_logs_from_journal()
    expected = XorgDrv(driver='qxl', has_options=False)
    actual = xorgdriverlib.check_drv_and_options('qxl', xorg_logs)
    assert expected == actual


def test_check_drv_and_options_intel_driver(monkeypatch):

    def get_xorg_logs_from_journal_mocked():
        return _read_log_file(os.path.join(CUR_DIR, 'files/journalctl-xorg-intel'))

    monkeypatch.setattr(xorgdriverlib, 'get_xorg_logs_from_journal', get_xorg_logs_from_journal_mocked)
    xorg_logs = xorgdriverlib.get_xorg_logs_from_journal()
    expected = XorgDrv(driver='intel', has_options=True)
    actual = xorgdriverlib.check_drv_and_options('intel', xorg_logs)
    assert expected == actual


def test_actor_with_deprecated_driver_without_options(current_actor_context, monkeypatch):

    def get_xorg_logs_from_journal_mocked():
        return _read_log_file(os.path.join(CUR_DIR, 'files/journalctl-xorg-qxl'))

    monkeypatch.setattr(xorgdriverlib, 'get_xorg_logs_from_journal', get_xorg_logs_from_journal_mocked)
    current_actor_context.run()
    facts = list(current_actor_context.consume(XorgDrvFacts))
    assert facts and len(facts[0].xorg_drivers) == 1
    assert (facts[0].xorg_drivers)[0].driver == 'qxl'
    assert (facts[0].xorg_drivers)[0].has_options is False


def test_actor_with_deprecated_driver_with_options(current_actor_context, monkeypatch):

    def get_xorg_logs_from_journal_mocked():
        return _read_log_file(os.path.join(CUR_DIR, 'files/journalctl-xorg-intel'))

    monkeypatch.setattr(xorgdriverlib, 'get_xorg_logs_from_journal', get_xorg_logs_from_journal_mocked)
    current_actor_context.run()
    facts = list(current_actor_context.consume(XorgDrvFacts))
    assert facts and len(facts[0].xorg_drivers) == 1
    assert (facts[0].xorg_drivers)[0].driver == 'intel'
    assert (facts[0].xorg_drivers)[0].has_options is True


def test_actor_without_deprecated_driver(current_actor_context, monkeypatch):

    def get_xorg_logs_from_journal_mocked():
        return _read_log_file(os.path.join(CUR_DIR, 'files/journalctl-xorg-without-qxl'))

    monkeypatch.setattr(xorgdriverlib, 'get_xorg_logs_from_journal', get_xorg_logs_from_journal_mocked)
    current_actor_context.run()
    facts = current_actor_context.consume(XorgDrvFacts)
    assert facts and len(facts[0].xorg_drivers) == 0
