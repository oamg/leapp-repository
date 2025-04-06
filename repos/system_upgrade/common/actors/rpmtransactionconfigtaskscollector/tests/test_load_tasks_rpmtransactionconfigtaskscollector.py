import logging

import pytest

import leapp.libraries.actor.rpmtransactionconfigtaskscollector as rpm_transaction_cfg_actor_lib
from leapp.configs.actor.rpm import (
    TRANSACTION_CFG_SECTION_NAME,
    Transaction_ToInstall,
    Transaction_ToKeep,
    Transaction_ToRemove
)
from leapp.libraries.actor.rpmtransactionconfigtaskscollector import load_tasks, load_tasks_file
from leapp.libraries.common.testutils import _make_default_config, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, RPM

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'


@pytest.mark.parametrize(
    (
        'to_install_file',
        'to_keep_file',
        'to_remove_file',
        'to_install_config',
        'to_keep_config',
        'to_remove_config',
        'to_install',
        'to_keep',
        'to_remove',
    ),
    (
        (
            'a\n b\n  c \n\n\nc\na\nc\nb',
            'a\n b\n  c \n\n\nc\na\nc\nb',
            'a\n b\n  c \n\n\nc\na\nc\nb',
            [],
            [],
            [],
            frozenset(('a', 'b')),
            frozenset(('a', 'b', 'c')),
            frozenset(('a', 'b', 'c')),
        ),
        (
            'a\n b\n  c \n\n\nc\na\nc\nb',
            'a\n b\n  c \n\n\nc\na\nc\nb',
            'a\n b\n  c \n\n\nc\na\nc\nb',
            ['a', 'd'],
            ['a', 'd'],
            ['a', 'd'],
            frozenset(('a', 'b', 'd')),
            frozenset(('a', 'b', 'c', 'd')),
            frozenset(('a', 'b', 'c', 'd')),
        ),
        (
            '',
            '\n',
            '',
            ['a', 'b', 'c', 'c', 'a', 'c', 'b'],
            ['a', 'b', 'c', 'c', 'a', 'c', 'b'],
            ['a', 'b', 'c', 'c', 'a', 'c', 'b'],
            frozenset(('a', 'b')),
            frozenset(('a', 'b', 'c')),
            frozenset(('a', 'b', 'c')),
        ),
    )
)
def test_load_tasks(to_install_file,
                    to_keep_file,
                    to_remove_file,
                    to_install_config,
                    to_keep_config,
                    to_remove_config,
                    to_install,
                    to_keep,
                    to_remove,
                    tmpdir,
                    monkeypatch,
                    ):

    def consume_signed_rpms_mocked(*models):
        installed = [
            RPM(name='c', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
                pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')
            ]
        yield DistributionSignedRPM(items=installed)

    monkeypatch.setattr(api, "consume", consume_signed_rpms_mocked)

    # Set values in the legacy configuration files
    tmpdir.join('to_install').write(to_install_file)
    tmpdir.join('to_keep').write(to_keep_file)
    tmpdir.join('to_remove').write(to_remove_file)

    # Simulate how the new actor config will come to us
    config = {
        'transaction': {
            'to_install': to_install_config,
            'to_keep': to_keep_config,
            'to_remove': to_remove_config,
        }
    }

    m = load_tasks(config, logging, base_dir=tmpdir.strpath)
    # c is not going to be in "to_install" as it is already installed
    assert frozenset(m.to_install) == to_install
    assert frozenset(m.to_keep) == to_keep
    assert frozenset(m.to_remove) == to_remove


def test_load_tasks_file(tmpdir):
    f = tmpdir.join('to_install')
    f.write('a\n b\n  c \n\n\nc\na\nc\nb')
    assert set(load_tasks_file(f.strpath, logging)) == set(['a', 'b', 'c'])
    f = tmpdir.join('to_keep')
    f.write(' ')
    assert set(load_tasks_file(f.strpath, logging)) == set([])


def test_config_is_reflected_in_actors_output(monkeypatch):
    monkeypatch.setattr(rpm_transaction_cfg_actor_lib, 'load_tasks_file', lambda *args, **kwargs: set())
    msgs = [DistributionSignedRPM(items=[])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))

    config = _make_default_config((Transaction_ToInstall, Transaction_ToKeep, Transaction_ToRemove))
    config[TRANSACTION_CFG_SECTION_NAME][Transaction_ToInstall.name] = ['install-a', 'install-b']
    config[TRANSACTION_CFG_SECTION_NAME][Transaction_ToRemove.name] = ['remove-a', 'remove-b']
    config[TRANSACTION_CFG_SECTION_NAME][Transaction_ToKeep.name] = ['keep-a', 'keep-b']

    logger = logger_mocked()

    produced_transaction_cfg = rpm_transaction_cfg_actor_lib.load_tasks(config, logger)
    assert produced_transaction_cfg.to_install == ['install-a', 'install-b']
    assert produced_transaction_cfg.to_remove == ['remove-a', 'remove-b']
    assert produced_transaction_cfg.to_keep == ['keep-a', 'keep-b']
