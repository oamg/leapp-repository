from leapp.models import KnownHostsProxyConfig, Report


def test_sssdchecks__no_file(current_actor_context):
    config = KnownHostsProxyConfig()
    current_actor_context.feed(config)
    current_actor_context.run()
    reports = current_actor_context.consume(Report)
    assert not reports


def test_sssdchecks__files(current_actor_context):
    sssd_files = ['/tmp/file1', '/tmp/file2']
    ssh_files = ['/tmp/file3', '/tmp/file4']
    all_files = sssd_files + ssh_files

    config = KnownHostsProxyConfig(sssd_config_files=sssd_files, ssh_config_files=ssh_files)
    current_actor_context.feed(config)
    current_actor_context.run()
    reports = current_actor_context.consume(Report)

    assert len(reports) == 1

    report = reports[0].report
    assert report['title'] == 'The sss_ssh_knownhostsproxy will be replaced by sss_ssh_knownhosts'
    assert 'sss_ssh_knownhosts tool.' in report['summary']

    FMT_LIST_SEPARATOR = '\n    - '
    assert "{}{}".format(FMT_LIST_SEPARATOR, FMT_LIST_SEPARATOR.join(all_files)) in report['summary']
