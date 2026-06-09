import os

import pytest

from leapp.libraries.actor import scanraid
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import DistributionSignedRPM, MDArray, RaidInfo, RPM

_MDADM_RPM = RPM(
    name='mdadm',
    version='4.2',
    release='1.el9',
    epoch='0',
    packager='',
    arch='x86_64',
    pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'
)

MDADM_SCAN_WITH_ARRAY = (
    'ARRAY /dev/md0 level=raid1 num-devices=2 metadata=1.2 '
    'name=localhost.localdomain:0 UUID=c4acea6e:d56e1598:91822e3f:fb26832c\n'
)

MDADM_SCAN_WITH_TWO_ARRAYS = (
    'ARRAY /dev/md0 metadata=1.2 UUID=c4acea6e:d56e1598:91822e3f:fb26832c\n'
    'ARRAY /dev/md1 metadata=1.2 UUID=5eb8cf98:a8d13c2e:3e91b4ca:2e1ac678\n'
)


class RunMocked:

    def __init__(self, stdout='', raise_err=False):
        self.called = 0
        self.args = None
        self.stdout = stdout
        self.raise_err = raise_err

    def __call__(self, args, encoding=None):
        self.called += 1
        self.args = args
        if self.raise_err:
            raise CalledProcessError(
                message='A Leapp Command Error occurred.',
                command=args,
                result={'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': 'fake', 'stderr': 'fake'}
            )
        assert args == scanraid.MDADM_SCAN_CMD
        return {'stdout': self.stdout}


def test_mdadm_not_installed(monkeypatch):
    msgs = [DistributionSignedRPM(items=[])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    scanraid.process()

    assert not api.produce.called


def test_mdadm_installed_with_active_arrays(monkeypatch):
    run_mocked = RunMocked(stdout=MDADM_SCAN_WITH_ARRAY)
    monkeypatch.setattr(scanraid, 'run', run_mocked)
    monkeypatch.setattr(os.path, 'exists', lambda path: path == '/usr/sbin/mdadm')

    msgs = [DistributionSignedRPM(items=[_MDADM_RPM])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    scanraid.process()

    assert run_mocked.called == 1
    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1
    produced = api.produce.model_instances[0]
    assert isinstance(produced, RaidInfo)
    assert produced.md_arrays == [MDArray(UUID='c4acea6e:d56e1598:91822e3f:fb26832c')]
    assert produced.dmraid_used is False


def test_mdadm_installed_with_multiple_arrays(monkeypatch):
    run_mocked = RunMocked(stdout=MDADM_SCAN_WITH_TWO_ARRAYS)
    monkeypatch.setattr(scanraid, 'run', run_mocked)
    monkeypatch.setattr(os.path, 'exists', lambda path: path == '/usr/sbin/mdadm')

    msgs = [DistributionSignedRPM(items=[_MDADM_RPM])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    scanraid.process()

    produced = api.produce.model_instances[0]
    assert [md_array.UUID for md_array in produced.md_arrays] == [
        'c4acea6e:d56e1598:91822e3f:fb26832c',
        '5eb8cf98:a8d13c2e:3e91b4ca:2e1ac678',
    ]


def test_mdadm_installed_no_active_arrays(monkeypatch):
    run_mocked = RunMocked(stdout='')
    monkeypatch.setattr(scanraid, 'run', run_mocked)
    monkeypatch.setattr(os.path, 'exists', lambda path: path == '/usr/sbin/mdadm')

    msgs = [DistributionSignedRPM(items=[_MDADM_RPM])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    scanraid.process()

    assert run_mocked.called == 1
    assert not api.produce.called


def test_mdadm_installed_scan_failure(monkeypatch):
    run_mocked = RunMocked(raise_err=True)
    monkeypatch.setattr(scanraid, 'run', run_mocked)
    monkeypatch.setattr(os.path, 'exists', lambda path: path == '/usr/sbin/mdadm')
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    msgs = [DistributionSignedRPM(items=[_MDADM_RPM])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    scanraid.process()

    assert run_mocked.called == 1
    assert not api.produce.called
    assert api.current_logger.warnmsg


def test_mdadm_installed_no_mdadm_binary(monkeypatch):
    run_mocked = RunMocked()
    monkeypatch.setattr(scanraid, 'run', run_mocked)
    monkeypatch.setattr(os.path, 'exists', lambda path: False)

    msgs = [DistributionSignedRPM(items=[_MDADM_RPM])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    scanraid.process()

    assert not run_mocked.called
    assert not api.produce.called
