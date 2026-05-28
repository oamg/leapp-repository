import os
import tempfile

import pytest

from leapp.libraries.actor import scanraid
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, RaidInfo, RPM


_MDADM_RPM = RPM(
    name='mdadm',
    version='4.2',
    release='1.el9',
    epoch='0',
    packager='',
    arch='x86_64',
    pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'
)

MDSTAT_WITH_ACTIVE_ARRAYS = """\
Personalities : [raid1]
md0 : active raid1 sda1[0] sdb1[1]
      1048512 blocks super 1.2 [2/2] [UU]

unused devices: <none>
"""

MDSTAT_NO_ACTIVE_ARRAYS = """\
Personalities : [raid1]
unused devices: <none>
"""

MDSTAT_INACTIVE_ARRAY = """\
Personalities : [raid1]
md0 : inactive sda1[0] sdb1[1]
      1048512 blocks super 1.2

unused devices: <none>
"""


def _write_mdstat(directory, content):
    path = os.path.join(directory, 'mdstat')
    with open(path, 'w') as f:
        f.write(content)
    return path


def test_mdadm_not_installed(monkeypatch):
    msgs = [DistributionSignedRPM(items=[])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    scanraid.process()

    assert not api.produce.called


def test_mdadm_installed_with_active_arrays(monkeypatch, leapp_tmpdir):
    mdstat_path = _write_mdstat(leapp_tmpdir, MDSTAT_WITH_ACTIVE_ARRAYS)
    monkeypatch.setattr(scanraid, 'PROC_MDSTAT', mdstat_path)

    msgs = [DistributionSignedRPM(items=[_MDADM_RPM])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    scanraid.process()

    assert api.produce.called == 1
    assert len(api.produce.model_instances) == 1
    produced = api.produce.model_instances[0]
    assert isinstance(produced, RaidInfo)
    assert produced.mdraid_used is True
    assert produced.dmraid_used is False


def test_mdadm_installed_no_active_arrays(monkeypatch, leapp_tmpdir):
    mdstat_path = _write_mdstat(leapp_tmpdir, MDSTAT_NO_ACTIVE_ARRAYS)
    monkeypatch.setattr(scanraid, 'PROC_MDSTAT', mdstat_path)

    msgs = [DistributionSignedRPM(items=[_MDADM_RPM])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    scanraid.process()

    assert not api.produce.called


def test_mdadm_installed_inactive_array(monkeypatch, leapp_tmpdir):
    mdstat_path = _write_mdstat(leapp_tmpdir, MDSTAT_INACTIVE_ARRAY)
    monkeypatch.setattr(scanraid, 'PROC_MDSTAT', mdstat_path)

    msgs = [DistributionSignedRPM(items=[_MDADM_RPM])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    scanraid.process()

    assert not api.produce.called


def test_mdadm_installed_no_mdstat_file(monkeypatch, leapp_tmpdir):
    monkeypatch.setattr(scanraid, 'PROC_MDSTAT', os.path.join(leapp_tmpdir, 'nonexistent'))

    msgs = [DistributionSignedRPM(items=[_MDADM_RPM])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    scanraid.process()

    assert not api.produce.called
