from leapp.libraries.actor import enable_lvm_autoactivation
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, RPM, UpgradeInitramfsTasks


def test_emit_lvm_autoactivation_instructions_produces_correct_message(monkeypatch):
    """Test that emit_lvm_autoactivation_instructions produces UpgradeInitramfsTasks with correct files."""
    lvm_package = RPM(
        name='lvm2',
        version='2',
        release='1',
        epoch='1',
        packager='',
        arch='x86_64',
        pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'
    )

    msgs = [
        DistributionSignedRPM(items=[lvm_package])
    ]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    enable_lvm_autoactivation.emit_lvm_autoactivation_instructions()

    assert api.produce.called == 1

    produced_msg = api.produce.model_instances[0]

    assert isinstance(produced_msg, UpgradeInitramfsTasks)

    expected_files = [
        '/usr/sbin/pvscan',
        '/usr/sbin/vgchange',
        '/usr/lib/udev/rules.d/69-dm-lvm.rules'
    ]
    assert produced_msg.include_files == expected_files


def test_no_action_if_lvm_rpm_missing(monkeypatch):
    msgs = [
        DistributionSignedRPM(items=[])
    ]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    enable_lvm_autoactivation.emit_lvm_autoactivation_instructions()

    assert api.produce.called == 0
