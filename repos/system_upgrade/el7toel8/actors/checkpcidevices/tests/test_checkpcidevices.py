from leapp.models import CheckResult, PCIDevices, PCIDevice


def test_no_unsupported_devices(current_actor_context):
    devices = [
        {
            'slot': '03:00.0',
            'dev_cls': 'Serial Attached SCSI Controller',
            'vendor': 'VMWare',
            'name': 'PVSCSI SCSI Controller',
            'subsystem_name': 'SCSI Controller',
            'subsystem_vendor': 'VMWare'
        }
    ]

    current_actor_context.feed(PCIDevices(devices=map(lambda x: PCIDevice(**x), devices)))
    current_actor_context.run()
    assert not current_actor_context.consume(CheckResult)


def test_unsupported_lsi_scsi(current_actor_context):
    devices = [
        {
            'slot': '02:01.0',
            'dev_cls': 'SCSI storage controller',
            'vendor': 'LSI Logic / Symbios Logic',
            'name': '53c1030 PCI-X Fusion-MPT Dual Ultra320 SCSI',
            'subsystem_name': 'SCSI Controller',
            'subsystem_vendor': 'LSI Logix / Symbios Logic'
        },
        {
            'slot': '03:00.0',
            'dev_cls': 'Serial Attached SCSI Controller',
            'vendor': 'VMWare',
            'name': 'PVSCSI SCSI Controller',
            'subsystem_name': 'SCSI Controller',
            'subsystem_vendor': 'VMWare'
        },
        {
            'slot': '13:00.0',
            'dev_cls': 'Serial Attached SCSI Controller',
            'vendor': 'LSI Logic / Symbios Logic',
            'name': 'SAS1068 PCI-X Fusion-MPT SAS',
            'subsystem_name': 'SCSI Controller',
            'subsystem_vendor': 'VMWare'
        }
    ]

    error_summary = 'LSI Logic SCSI Controller is not supported'

    current_actor_context.feed(PCIDevices(devices=map(lambda x: PCIDevice(**x), devices)))
    current_actor_context.run()
    assert current_actor_context.consume(CheckResult)
    assert current_actor_context.consume(CheckResult)[0].summary == error_summary


def test_no_devices(current_actor_context):
    current_actor_context.feed(PCIDevices(devices=[]))
    current_actor_context.run()
    assert not current_actor_context.consume(CheckResult)
