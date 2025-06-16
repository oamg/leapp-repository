from leapp.models import KnownHostsProxyConfig, Report


def test_sssdchecks__no_file(current_actor_context):
    config = KnownHostsProxyConfig()
    current_actor_context.feed(config)
    current_actor_context.run()
    reports = current_actor_context.consume(Report)
    assert len(reports) == 0

def test_sssdchecks__files(current_actor_context):
    sssd_files = ['/tmp/file1', '/tmp/file2']
    ssh_files =  ['/tmp/file3', '/tmp/file4']
    all_files = sssd_files + ssh_files

    config = KnownHostsProxyConfig(sssd_config_files = sssd_files, ssh_config_files = ssh_files)
    current_actor_context.feed(config)
    current_actor_context.run()
    reports = current_actor_context.consume(Report)

    assert len(reports) == 1

    report = reports[0].report
    assert report['title'] == 'sss_ssh_knownhosts replaces sss_ssh_knownhostsproxy.'
    assert 'sss_ssh_knownhosts tool' in report['summary']

    resources = report['detail']['related_resources']
    assert len(resources) == len(all_files)
    for res in resources:
        assert res['scheme'] == 'file'
        assert res['title'] in all_files
