from leapp.models import CheckResult, PCIDevices, PCIDevice
from leapp.snactor.fixture import current_actor_context


def create_pcidevices(items):
    attrs = [
        'slot',
        'cls',
        'vendor',
        'name',
        'subsystem_vendor',
        'subsystem_name',
        'rev',
        'progif']

    pcidevices = PCIDevices()
    for i in items:
        d = PCIDevice()
        for attr in attrs:
            setattr(d, attr, i.get(attr, ''))
        pcidevices.append(d)

    return pcidevices


def test_no_unsupported_devices(current_actor_context):
    devices = [
        {
            'slot': '03:00.0',
            'cls': 'Serial Attached SCSI Controller',
            'vendor': 'VMWare',
            'device': 'PVSCSI SCSI Controller',
            'rev': '02'
        }
    ]
    current_actor_context.feed(create_pcidevices(devices))
    current_actor_context.run()
    assert not current_actor_context.consume(CheckResult)


def test_unsupported_lsi_scsi(current_actor_context):
    devices = [
        {
            'slot': '02:01.0',
            'cls': 'SCSI storage controller',
            'vendor': 'LSI Logic / Symbios Logic',
            'device': '53c1030 PCI-X Fusion-MPT Dual Ultra320 SCSI',
            'rev': '01'
        },
        {
            'slot': '03:00.0',
            'cls': 'Serial Attached SCSI Controller',
            'vendor': 'VMWare',
            'device': 'PVSCSI SCSI Controller',
            'rev': '02'
        },
        {
            'slot': '13:00.0',
            'cls': 'Serial Attached SCSI Controller',
            'vendor': 'LSI Logic / Symbios Logic',
            'device': 'SAS1068 PCI-X Fusion-MPT SAS',
            'rev': '01'
        }
    ]

    error_summary = 'LSI Logic SCSI Controller is not supported'

    current_actor_context.feed(create_pcidevices(devices))
    current_actor_context.run()
    assert current_actor_context.consume(CheckResult)
    assert current_actor_context.consume(CheckResult)[0].summary == error_summary
