import leapp.libraries.common.tcpwrappersutils as lib
from leapp.models import DaemonList, TcpWrappersFacts


def test_config_applies_to_daemon_simple():
    daemon_list = DaemonList(value=['vsftpd'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])

    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True
    assert lib.config_applies_to_daemon(facts, 'VsfTpd') is True
    assert lib.config_applies_to_daemon(facts, 'ftp') is False
    assert lib.config_applies_to_daemon(facts, 'foo') is False


def test_config_applies_to_daemon_multiple_lists():
    list1 = DaemonList(value=['vsftpd', 'sendmail'])
    list2 = DaemonList(value=['postfix'])
    facts = TcpWrappersFacts(daemon_lists=[list1, list2])

    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True
    assert lib.config_applies_to_daemon(facts, 'sendmail') is True
    assert lib.config_applies_to_daemon(facts, 'postfix') is True
    assert lib.config_applies_to_daemon(facts, 'foo') is False


def test_config_applies_to_daemon_except():
    list1 = DaemonList(value=['all', 'except', 'sendmail'])
    list2 = DaemonList(value=['postfix'])
    facts = TcpWrappersFacts(daemon_lists=[list1, list2])

    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True
    assert lib.config_applies_to_daemon(facts, 'sendmail') is False
    assert lib.config_applies_to_daemon(facts, 'postfix') is True
    assert lib.config_applies_to_daemon(facts, 'foo') is True

    list1 = DaemonList(value=['all', 'except', 'b*', 'EXCEPT', 'bar'])
    facts = TcpWrappersFacts(daemon_lists=[list1])
    assert lib.config_applies_to_daemon(facts, 'foo') is True
    assert lib.config_applies_to_daemon(facts, 'bar') is True
    assert lib.config_applies_to_daemon(facts, 'baar') is False

    list1 = DaemonList(value=['all', 'except', 'vsftpd'])
    facts = TcpWrappersFacts(daemon_lists=[list1])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is False

    list1 = DaemonList(value=['all', 'except', 'all', 'except', 'vsftpd'])
    facts = TcpWrappersFacts(daemon_lists=[list1])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True

    list1 = DaemonList(value=['all', 'except', 'all', 'except', 'all', 'except', 'vsftpd'])
    facts = TcpWrappersFacts(daemon_lists=[list1])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is False


def test_config_applies_to_daemon_except_empty():
    daemon_list = DaemonList(value=['all', 'except'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True


def test_config_applies_to_daemon_with_host():
    list1 = DaemonList(value=['vsftpd@localhost', 'sendmail'])
    list2 = DaemonList(value=['postfix'])
    facts = TcpWrappersFacts(daemon_lists=[list1, list2])

    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True
    assert lib.config_applies_to_daemon(facts, 'sendmail') is True
    assert lib.config_applies_to_daemon(facts, 'postfix') is True
    assert lib.config_applies_to_daemon(facts, 'foo') is False


def test_config_applies_to_daemon_with_host_except():
    daemon_list = DaemonList(value=['vsftpd@localhost', 'except', 'vsftpd'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is False

    # It works like this for simplicity.
    daemon_list = DaemonList(value=['vsftpd@localhost', 'except', 'vsftpd@localhost'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True

    daemon_list = DaemonList(value=['vsftpd@localhost'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True

    daemon_list = DaemonList(value=['all', 'except', 'vsftpd@localhost'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True

    daemon_list = DaemonList(value=['all', 'except', 'all', 'except', 'vsftpd@localhost'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True

    daemon_list = DaemonList(value=['all', 'except', 'all', 'except', 'all',
                                    'except', 'vsftpd@localhost'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True

    daemon_list = DaemonList(value=['all', 'except', 'all', 'except', 'all', 'except', 'all',
                                    'except', 'vsftpd@localhost'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True


def test_config_applies_to_daemon_empty():
    daemon_list = DaemonList(value=[''])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is False

    daemon_list = DaemonList(value=[])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is False


def test_config_applies_to_daemon_whole_word():
    daemon_list = DaemonList(value=['ftp'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is False


def test_config_applies_to_daemon_asterisk_wildcard():
    daemon_list = DaemonList(value=['*ftp*'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True

    daemon_list = DaemonList(value=['************'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True

    daemon_list = DaemonList(value=['*'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True

    daemon_list = DaemonList(value=['*foo*'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is False


def test_config_applies_to_daemon_question_mark_wildcard():
    daemon_list = DaemonList(value=['vs?tpd'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True

    daemon_list = DaemonList(value=['vsf?tpd'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is False

    daemon_list = DaemonList(value=['?'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is False

    daemon_list = DaemonList(value=['??????'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True


def test_config_applies_to_daemon_all_wildcard():
    daemon_list = DaemonList(value=['all'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True

    daemon_list = DaemonList(value=['aLl'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is True

    daemon_list = DaemonList(value=['al'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is False

    daemon_list = DaemonList(value=['ll'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is False

    daemon_list = DaemonList(value=['valld'])
    facts = TcpWrappersFacts(daemon_lists=[daemon_list])
    assert lib.config_applies_to_daemon(facts, 'vsftpd') is False
