import pytest
import os

from tempfile import NamedTemporaryFile

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import sssdfacts


def make_tmp_file(contents: str, *, dir: str| None = None) -> NamedTemporaryFile:
    file = NamedTemporaryFile(mode='w+t', prefix='test.sssdfacts.', dir=dir)
    file.write(contents)
    file.seek(0)
    # The file will be deleted on closure, so keep it open.
    return file

def make_sssd_config_file(configured: bool, enabled: bool) -> NamedTemporaryFile:
    contents = f"""
    [sssd]
    {'#' if not configured else ''}services = pam
    """

    contents = '[sssd]\n'
    if configured:
        if not enabled:
            contents += "# "
        contents += 'services = pam\n'
    contents += '# last line\n'

    return make_tmp_file(contents)

def make_ssh_config_file(configured: bool, enabled: bool, *, dir: str| None = None) -> NamedTemporaryFile:
    contents = '# 1st line\n'
    if configured:
        if not enabled:
            contents += "# "
        contents += 'ProxyCommand /usr/bin/sss_ssh_knownhostsproxy -p %p %h\n'
    contents += '# last line\n'
    return make_tmp_file(contents, dir=dir)

def test_sssdfacts__missing_config():
    facts = sssdfacts.get_facts(sssd_config=['/etc/missing-file'],
                                ssh_config=['/etc/missing-file'])

    assert len(facts.sssd_config_files) == 0
    assert len(facts.ssh_config_files) == 0

def test_sssdfacts__empty_config():
    facts = sssdfacts.get_facts(sssd_config=['/dev/null'],
                                ssh_config=['/dev/null'])
    assert len(facts.sssd_config_files) == 0
    assert len(facts.ssh_config_files) == 0

@pytest.mark.parametrize('svc_configured', [(True), (False)])
@pytest.mark.parametrize('svc_enabled', [(True), (False)])
def test_sssdfacts__ssh_service(svc_configured, svc_enabled):
    sssd_config = make_sssd_config_file(svc_configured, svc_enabled)

    facts = sssdfacts.get_facts(sssd_config=[sssd_config.name],
                                ssh_config=['/dev/null'])

    sssd_config.close()

    if svc_configured:
        assert len(facts.sssd_config_files) == 1
        assert sssd_config.name in facts.sssd_config_files
    else:
        assert len(facts.sssd_config_files) == 0

@pytest.mark.parametrize('proxy_configured', [(True), (False)])
@pytest.mark.parametrize('proxy_enabled', [(True), (False)])
def test_sssdfacts__knownhostsproxy(proxy_configured, proxy_enabled):
    ssh_config = make_ssh_config_file(proxy_configured, proxy_enabled)

    facts = sssdfacts.get_facts(sssd_config=['/dev/null'],
                                ssh_config=[ssh_config.name])

    ssh_config.close()

    if proxy_configured:
        assert len(facts.ssh_config_files) == 1
        assert ssh_config.name in facts.ssh_config_files
    else:
        assert len(facts.ssh_config_files) == 0

def test_sssdfacts__directory():
    dir = '/tmp/test.sssdfacts'
    os.mkdir(dir)
    ssh_config = make_ssh_config_file(True, True, dir=dir)

    facts = sssdfacts.get_facts(sssd_config=['/dev/null'],
                                ssh_config=[dir])

    ssh_config.close()
    os.rmdir(dir)

    assert len(facts.ssh_config_files) == 1
    assert ssh_config.name in facts.ssh_config_files

def test_sssdfacts__file_error():
    ssh_config = make_ssh_config_file(True, True)
    os.chmod(ssh_config.name, 0)

    exception = None
    try:
        sssdfacts.get_facts(sssd_config=['/dev/null'],
                            ssh_config=[ssh_config.name])
    except StopActorExecutionError as e:
        exception = e

    ssh_config.close()

    assert exception is not None
    assert isinstance(exception, StopActorExecutionError)
    assert str(exception) == 'Could not open file ' + ssh_config.name
    assert exception.details is not None
    assert 'Permission denied' in exception.details['details']
    assert ssh_config.name in exception.details['details']
