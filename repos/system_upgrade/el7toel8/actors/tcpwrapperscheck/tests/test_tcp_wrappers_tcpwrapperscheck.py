from leapp.libraries.actor.tcpwrapperscheck import config_affects_daemons
from leapp.models import DaemonList, TcpWrappersFacts


def test_empty_packages():
    """ Test with empty package list """
    w = TcpWrappersFacts(daemon_lists=[DaemonList(value=["ALL"])])
    p = []
    d = [("openssh", ["sshd"])]
    packages = config_affects_daemons(w, p, d)

    assert not packages


def test_empty_tcp_wrappers():
    """ Test with empty tcp_wrappers facts """
    w = TcpWrappersFacts(daemon_lists=[])
    p = ["openssh", "systemd", "pam"]
    d = [("openssh", ["sshd"])]
    packages = config_affects_daemons(w, p, d)

    assert not packages


def test_matching_package():
    """ Test with matching package, but not daemon """
    w = TcpWrappersFacts(daemon_lists=[DaemonList(value=["imap"])])
    p = ["openssh", "systemd", "pam"]
    d = [("openssh", ["sshd"])]
    packages = config_affects_daemons(w, p, d)

    assert not packages


def test_matching_daemon():
    """ Test with matching package with daemon """
    w = TcpWrappersFacts(daemon_lists=[DaemonList(value=["sshd"])])
    p = ["openssh", "systemd", "pam"]
    d = [("openssh", ["sshd"])]
    packages = config_affects_daemons(w, p, d)

    assert len(packages) == 1
    assert "openssh" in packages


def test_matching_all():
    """ Test with matching package with daemon """
    w = TcpWrappersFacts(daemon_lists=[DaemonList(value=["ALL"])])
    p = ["openssh", "systemd", "pam", "audit"]
    d = [("openssh", ["sshd"]), ("audit", ["auditd"])]
    packages = config_affects_daemons(w, p, d)

    assert len(packages) == 2
    assert "openssh" in packages
    assert "audit" in packages
