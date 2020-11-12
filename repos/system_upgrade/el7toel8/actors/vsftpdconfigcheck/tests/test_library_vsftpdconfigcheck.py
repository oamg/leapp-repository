from leapp.models import DaemonList, TcpWrappersFacts, VsftpdConfig, VsftpdFacts
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context


def test_actor_with_unsupported_tcpwrap_and_vsftpd_config(current_actor_context):
    config1 = VsftpdConfig(path='/etc/vsftpd/foo.conf', tcp_wrappers=False)
    config2 = VsftpdConfig(path='/etc/vsftpd/bar.conf', tcp_wrappers=True)
    vsftpd_facts = VsftpdFacts(configs=[config1, config2])
    daemon_list = DaemonList(value=['vsftpd'])
    tcpwrap_facts = TcpWrappersFacts(daemon_lists=[daemon_list])

    current_actor_context.feed(vsftpd_facts)
    current_actor_context.feed(tcpwrap_facts)
    current_actor_context.run()
    report_fields = current_actor_context.consume(Report)[0].report

    assert 'inhibitor' in report_fields['groups']
    assert 'foo.conf' not in report_fields['summary']
    assert 'bar.conf' in report_fields['summary']


def test_actor_with_unsupported_tcpwrap_multiple_unsupported_vsftpd_configs(current_actor_context):
    config1 = VsftpdConfig(path='/etc/vsftpd/foo.conf', tcp_wrappers=True)
    config2 = VsftpdConfig(path='/etc/vsftpd/bar.conf', tcp_wrappers=False)
    config3 = VsftpdConfig(path='/etc/vsftpd/goo.conf', tcp_wrappers=True)
    vsftpd_facts = VsftpdFacts(configs=[config1, config2, config3])
    daemon_list = DaemonList(value=['vsftpd'])
    tcpwrap_facts = TcpWrappersFacts(daemon_lists=[daemon_list])

    current_actor_context.feed(vsftpd_facts)
    current_actor_context.feed(tcpwrap_facts)
    current_actor_context.run()
    report_fields = current_actor_context.consume(Report)[0].report

    assert 'inhibitor' in report_fields['groups']
    assert 'foo.conf' in report_fields['summary']
    assert 'bar.conf' not in report_fields['summary']
    assert 'goo.conf' in report_fields['summary']


def test_actor_with_unsupported_tcpwrap_config(current_actor_context):
    config1 = VsftpdConfig(path='/etc/vsftpd/foo.conf', tcp_wrappers=False)
    config2 = VsftpdConfig(path='/etc/vsftpd/bar.conf', tcp_wrappers=None)
    vsftpd_facts = VsftpdFacts(configs=[config1, config2])
    daemon_list = DaemonList(value=['vsftpd'])
    tcpwrap_facts = TcpWrappersFacts(daemon_lists=[daemon_list])

    current_actor_context.feed(vsftpd_facts)
    current_actor_context.feed(tcpwrap_facts)
    current_actor_context.run()

    assert not current_actor_context.consume(Report)


def test_actor_with_unsupported_vsftpd_config(current_actor_context):
    config1 = VsftpdConfig(path='/etc/vsftpd/foo.conf', tcp_wrappers=False)
    config2 = VsftpdConfig(path='/etc/vsftpd/bar.conf', tcp_wrappers=True)
    vsftpd_facts = VsftpdFacts(configs=[config1, config2])
    daemon_list = DaemonList(value=['all', 'except', 'vsftpd'])
    tcpwrap_facts = TcpWrappersFacts(daemon_lists=[daemon_list])

    current_actor_context.feed(vsftpd_facts)
    current_actor_context.feed(tcpwrap_facts)
    current_actor_context.run()

    assert not current_actor_context.consume(Report)


def test_actor_with_supported_tcpwrap_and_vsftpd_config(current_actor_context):
    config1 = VsftpdConfig(path='/etc/vsftpd/foo.conf', tcp_wrappers=False)
    config2 = VsftpdConfig(path='/etc/vsftpd/bar.conf', tcp_wrappers=False)
    vsftpd_facts = VsftpdFacts(configs=[config1, config2])
    daemon_list = DaemonList(value=['all', 'except', 'vsftpd'])
    tcpwrap_facts = TcpWrappersFacts(daemon_lists=[daemon_list])

    current_actor_context.feed(vsftpd_facts)
    current_actor_context.feed(tcpwrap_facts)
    current_actor_context.run()

    assert not current_actor_context.consume(Report)
