import os

import pytest

from leapp.libraries.actor import sssdfacts

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def test_sssdfacts__missing_config():
    facts = sssdfacts.get_facts(sssd_config=['/etc/missing-file'],
                                ssh_config=['/etc/missing-file'])

    assert not facts.sssd_config_files
    assert not facts.ssh_config_files


def test_sssdfacts__empty_config():
    facts = sssdfacts.get_facts(sssd_config=['/dev/null'],
                                ssh_config=['/dev/null'])
    assert not facts.sssd_config_files
    assert not facts.ssh_config_files


@pytest.mark.parametrize('state', ['not_present', 'disabled', 'enabled'])
def test_sssdfacts__sssd_service(state):
    file = os.path.join(CUR_DIR, 'files', 'sssd_service_' + state + '.conf')
    facts = sssdfacts.get_facts(sssd_config=[file],
                                ssh_config=['/dev/null'])

    if state == 'not_present':
        assert not facts.sssd_config_files
    else:
        assert len(facts.sssd_config_files) == 1
        assert file in facts.sssd_config_files


@pytest.mark.parametrize('state', ['not_present', 'disabled', 'enabled'])
def test_sssdfacts__knownhostsproxy(state):
    file = os.path.join(CUR_DIR, 'files', 'ssh_proxy_' + state + '.conf')

    facts = sssdfacts.get_facts(sssd_config=['/dev/null'],
                                ssh_config=[file])

    if state == 'not_present':
        assert not facts.ssh_config_files
    else:
        assert len(facts.ssh_config_files) == 1
        assert file in facts.ssh_config_files


def test_sssdfacts__directory():
    dirpath = os.path.join(CUR_DIR, 'files')
    facts = sssdfacts.get_facts(sssd_config=['/dev/null'],
                                ssh_config=[dirpath])

    assert len(facts.ssh_config_files) == 3
    assert os.path.join(CUR_DIR, 'files', 'ssh_proxy_disabled.conf') in facts.ssh_config_files
    assert os.path.join(CUR_DIR, 'files', 'ssh_proxy_enabled.conf') in facts.ssh_config_files
    assert os.path.join(CUR_DIR, 'files', 'subdir', 'sub_ssh_proxy_enabled.conf') in facts.ssh_config_files
