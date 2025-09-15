from leapp.libraries.actor import enable_lvm_autoactivation
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import UpgradeInitramfsTasks


def test_emit_lvm_autoactivation_instructions_produces_correct_message(monkeypatch):
    """Test that emit_lvm_autoactivation_instructions produces UpgradeInitramfsTasks with correct files."""
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
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
