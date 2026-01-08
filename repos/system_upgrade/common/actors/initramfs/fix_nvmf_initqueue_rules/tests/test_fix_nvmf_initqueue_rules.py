import os
import tempfile

from leapp.libraries.actor import fix_nvmf_initqueue_rules
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import LiveModeConfig, NVMEDevice, NVMEInfo, TargetUserSpaceInfo, UpgradeInitramfsTasks


def test_replace_nvmf_initqueue_rules_no_nvme_devices(monkeypatch):
    """Test that replacement is skipped when no NVMe devices are detected."""
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    fix_nvmf_initqueue_rules.replace_nvmf_initqueue_rules()

    assert any('No NVMe devices detected' in msg for msg in api.current_logger.dbgmsg)


def test_replace_nvmf_initqueue_rules_livemode_enabled(monkeypatch):
    """Test that replacement is skipped when no LiveMode is enabled."""
    livemode_info = LiveModeConfig(
        is_enabled=True,
        squashfs_fullpath=''
    )

    nvme_device = NVMEDevice(
        sys_class_path='/sys/class/nvme/nvme0',
        name='nvme0',
        transport='fc'
    )
    nvme_info = NVMEInfo(devices=[nvme_device], hostid='test-hostid', hostnqn='test-hostnqn')

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[livemode_info, nvme_info]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    fix_nvmf_initqueue_rules.replace_nvmf_initqueue_rules()

    assert any('LiveMode is enabled.' in msg for msg in api.current_logger.dbgmsg)


def test_replace_nvmf_initqueue_rules_empty_nvme_devices(monkeypatch):
    """Test that replacement is skipped when NVMEInfo has no devices."""
    nvme_info = NVMEInfo(devices=[], hostid=None, hostnqn=None)

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[nvme_info]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    fix_nvmf_initqueue_rules.replace_nvmf_initqueue_rules()

    assert any('No NVMe devices detected' in msg for msg in api.current_logger.dbgmsg)


def test_replace_nvmf_initqueue_rules_success(monkeypatch):
    """Test successful replacement of nvmf initqueue rules."""
    with tempfile.TemporaryDirectory(prefix='leapp_test_') as tmpdir:
        nvmf_dir = os.path.join(tmpdir, 'usr/lib/dracut/modules.d/95nvmf')
        os.makedirs(nvmf_dir)

        target_rules_path = os.path.join(nvmf_dir, '95-nvmf-initqueue.rules')
        with open(target_rules_path, 'w') as f:
            f.write('# original rules')

        source_file = os.path.join(tmpdir, 'source_rules')
        with open(source_file, 'w') as f:
            f.write('# fixed rules content')

        nvme_device = NVMEDevice(
            sys_class_path='/sys/class/nvme/nvme0',
            name='nvme0',
            transport='fc'
        )
        nvme_info = NVMEInfo(devices=[nvme_device], hostid='test-hostid', hostnqn='test-hostnqn')
        userspace_info = TargetUserSpaceInfo(path=tmpdir, scratch='/tmp/scratch', mounts='/tmp/mounts')

        monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[nvme_info, userspace_info]))
        monkeypatch.setattr(api, 'current_logger', logger_mocked())
        monkeypatch.setattr(api, 'produce', produce_mocked())
        monkeypatch.setattr(api, 'get_actor_file_path', lambda x: source_file)

        fix_nvmf_initqueue_rules.replace_nvmf_initqueue_rules()

        # Verify the file was replaced
        with open(target_rules_path) as f:
            content = f.read()

        assert content == '# fixed rules content'

        # Verify UpgradeInitramfsTasks was produced
        assert api.produce.called == 1
        produced_msg = api.produce.model_instances[0]
        assert isinstance(produced_msg, UpgradeInitramfsTasks)
