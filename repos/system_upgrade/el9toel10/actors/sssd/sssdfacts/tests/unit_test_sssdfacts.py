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


def test_sssdfacts__non_utf8_file_is_skipped(leapp_tmpdir):
    non_utf8_file = os.path.join(leapp_tmpdir, 'binary.conf')
    with open(non_utf8_file, 'wb') as f:
        f.write(b'\xff\xfeservices = nss, pam\x00\x01')

    facts = sssdfacts.get_facts(sssd_config=[non_utf8_file],
                                ssh_config=['/dev/null'])

    assert not facts.sssd_config_files


def test_sssdfacts__non_utf8_file_in_directory_is_skipped(leapp_tmpdir):
    with open(os.path.join(leapp_tmpdir, 'binary.conf.swp'), 'wb') as f:
        f.write(b'\xff\xfeservices = nss, pam\x00\x01')
    valid_file = os.path.join(leapp_tmpdir, 'sssd.conf')
    with open(valid_file, 'w') as f:
        f.write('[sssd]\nservices = nss, pam\n')

    facts = sssdfacts.get_facts(sssd_config=[leapp_tmpdir],
                                ssh_config=['/dev/null'])

    assert len(facts.sssd_config_files) == 1
    assert valid_file in facts.sssd_config_files
