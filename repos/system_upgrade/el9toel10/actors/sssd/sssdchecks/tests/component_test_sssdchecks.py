import os
import stat

from tempfile import NamedTemporaryFile

from leapp.models import SSSDConfig, Report

def make_tmp_file() -> str:
    file = NamedTemporaryFile(mode='w+t', prefix='test.sssdfchecks.', delete=False)
    # The file will be deleted on closure, so keep it open.
    return file.name

def make_files(count: int) -> list[str]:
    files = []
    for i in range(count):
        files.append(make_tmp_file())

    return files

def test_sssdchecks__no_files(current_actor_context):
    config = SSSDConfig()
    current_actor_context.feed(config)
    current_actor_context.run()
    reports = current_actor_context.consume(Report)
    assert len(reports) == 0

def test_sssdchecks__files(current_actor_context):
    sssd_files = make_files(2)
    ssh_files = make_files(2)
    all_files = sssd_files + ssh_files

    config = SSSDConfig(sssd_config_files = sssd_files, ssh_config_files = ssh_files)
    current_actor_context.feed(config)
    current_actor_context.run()
    reports = current_actor_context.consume(Report)

    for file in all_files:
        os.unlink(file)

    assert len(reports) == 1

    report = reports[0].report
    assert report['title'] == 'sss_ssh_knownhosts replaces sss_ssh_knownhostsproxy.'
    assert 'sss_ssh_knownhosts tool' in report['summary']
    assert 'not writable: ' not in report['summary']

    resources = report['detail']['related_resources']
    assert len(resources) == len(all_files)
    for res in resources:
        assert res['scheme'] == 'file'
        assert res['title'] in all_files

def test_sssdchecks__file_error(current_actor_context):
    ssh_files = make_files(1)
    os.chmod(ssh_files[0], 0o444)

    config = SSSDConfig(ssh_config_files = ssh_files)
    current_actor_context.feed(config)
    current_actor_context.run()
    reports = current_actor_context.consume(Report)

    fstat = os.stat(ssh_files[0])
    assert stat.filemode(fstat.st_mode & stat.ST_MODE) == stat.filemode(0o444 & stat.ST_MODE)

    os.unlink(ssh_files[0])

    assert len(reports) == 1

    report = reports[0].report
    assert report['title'] == 'sss_ssh_knownhosts replaces sss_ssh_knownhostsproxy.'
    assert 'not writable: ' + ssh_files[0] in report['summary']