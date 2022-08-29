import os

import pytest

from leapp.libraries.actor.scanfilesfortargetuserspace import scan_files_to_copy
from leapp.libraries.common.testutils import produce_mocked
from leapp.libraries.stdlib import api


@pytest.fixture
def isfile_default_config():
    config = {
        '/etc/hosts': True
    }
    return config


def do_files_to_copy_contain_entry_with_src(files_to_copy, src):
    """Searches the files to be copied for an entry with src field that matches the given src."""
    is_present = False
    for file_to_copy in files_to_copy:
        if file_to_copy.src == src:
            is_present = True
            break
    return is_present


def make_mocked_isfile(configuration):
    """
    Creates mocked isfile function that returns values according the given configuration.

    The created function raises :class:`ValueError` should the unit under test try to "isfile"
    a path that is not present in the configuration.

    One global mocked function with configuration is error prone as individual test would
    have to return the configuration into the original state after execution.
    """

    def mocked_isfile(path):
        if path in configuration:
            return configuration[path]
        error_msg = 'The actor tried to isfile a path that it should not. (path `{0}`)'
        raise ValueError(error_msg.format(path))
    return mocked_isfile


def test_etc_hosts_present(monkeypatch, isfile_default_config):
    """Tests whether /etc/hosts is identified as "to be copied" into target userspace when it is present."""
    mocked_isfile = make_mocked_isfile(isfile_default_config)
    actor_produces = produce_mocked()
    monkeypatch.setattr(os.path, 'isfile', mocked_isfile)
    monkeypatch.setattr(api, 'produce', actor_produces)

    scan_files_to_copy()

    fail_msg = 'Produced unexpected number of messages.'
    assert len(actor_produces.model_instances) == 1, fail_msg

    preupgrade_task_msg = actor_produces.model_instances[0]

    fail_msg = 'Didn\'t identify any files to copy into target userspace (at least /etc/hosts should be).'
    assert preupgrade_task_msg.copy_files, fail_msg

    should_copy_hostsfile = do_files_to_copy_contain_entry_with_src(preupgrade_task_msg.copy_files, '/etc/hosts')
    assert should_copy_hostsfile, 'Failed to identify /etc/hosts as a file to be copied into target userspace.'

    fail_msg = 'Produced message contains rpms to be installed, however only copy files field should be populated.'
    assert not preupgrade_task_msg.install_rpms, fail_msg


def test_etc_hosts_missing(monkeypatch, isfile_default_config):
    """Tests whether /etc/hosts is not identified as "to be copied" into target userspace when it is missing."""
    isfile_default_config['/etc/hosts'] = False  # The file is not present or is a directory (-> should not be copied)
    mocked_isfile = make_mocked_isfile(isfile_default_config)
    actor_produces = produce_mocked()

    monkeypatch.setattr(os.path, 'isfile', mocked_isfile)
    monkeypatch.setattr(api, 'produce', actor_produces)

    scan_files_to_copy()

    assert len(actor_produces.model_instances) == 1, 'Produced unexpected number of messages.'

    preupgrade_task_msg = actor_produces.model_instances[0]
    should_copy_hostsfile = do_files_to_copy_contain_entry_with_src(preupgrade_task_msg.copy_files, '/etc/hosts')
    assert not should_copy_hostsfile, 'Identified /etc/hosts as a file to be copied even if it doesn\'t exists'

    fail_msg = 'Produced message contains rpms to be installed, however only copy files field should be populated.'
    assert not preupgrade_task_msg.install_rpms, fail_msg
