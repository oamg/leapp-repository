from subprocess import call

from leapp.libraries.actor import yumupgradability


def test_secure_yum_upgradability(monkeypatch):
    """
    Test Secure Yum upgradability library function

    :return: Indicates Pass/Fail - whether tests succeeded
    """

    monkeypatch.setattr(yumupgradability, "CMDS", [['whoami'], ['ls']])
    monkeypatch.setattr(yumupgradability, 'run_cmd', call)
    expected_yellow_flag = False
    actual_yellow_flag = yumupgradability.secure_yum_upgradability()
    assert actual_yellow_flag == expected_yellow_flag
