import pytest
import os

from leapp.libraries.actor import sssdfacts


CUR_DIR = os.path.dirname(os.path.abspath(__file__))

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

@pytest.mark.parametrize('step', ['not_present', 'disabled', 'enabled'])
def test_sssdfacts__sssd_service(step):
    file = os.path.join(CUR_DIR, 'files', 'sssd_service_' + step + '.conf')
    facts = sssdfacts.get_facts(sssd_config=[file],
                                ssh_config=['/dev/null'])

    if step == 'not_present':
        assert len(facts.sssd_config_files) == 0
    else:
        assert len(facts.sssd_config_files) == 1
        assert file in facts.sssd_config_files

@pytest.mark.parametrize('step', ['not_present', 'disabled', 'enabled'])
def test_sssdfacts__knownhostsproxy(step):
    file = os.path.join(CUR_DIR, 'files', 'ssh_proxy_' + step + '.conf')

    facts = sssdfacts.get_facts(sssd_config=['/dev/null'],
                                ssh_config=[file])

    if step == 'not_present':
        assert len(facts.ssh_config_files) == 0
    else:
        assert len(facts.ssh_config_files) == 1
        assert file in facts.ssh_config_files

def test_sssdfacts__directory():
    dir = os.path.join(CUR_DIR, 'files')
    facts = sssdfacts.get_facts(sssd_config=['/dev/null'],
                                ssh_config=[dir])

    assert len(facts.ssh_config_files) == 3
    assert os.path.join(CUR_DIR, 'files', 'ssh_proxy_disabled.conf') in facts.ssh_config_files
    assert os.path.join(CUR_DIR, 'files', 'ssh_proxy_enabled.conf') in facts.ssh_config_files
    assert os.path.join(CUR_DIR, 'files', 'subdir', 'sub_ssh_proxy_enabled.conf') in facts.ssh_config_files
