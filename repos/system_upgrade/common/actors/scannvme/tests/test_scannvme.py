import pytest

from leapp.libraries.actor import scannvme
from leapp.models import NVMEDevice


def test_get_transport_type_file_missing(monkeypatch):
    """Test that NVMEMissingTransport is raised when transport file does not exist."""
    monkeypatch.setattr('os.path.join', lambda *args: '/sys/class/nvme/nvme0/transport')
    monkeypatch.setattr('os.path.exists', lambda path: False)

    with pytest.raises(scannvme.NVMEMissingTransport):
        scannvme._get_transport_type('/sys/class/nvme/nvme0')


def test_get_transport_type_file_empty(monkeypatch):
    """Test that NVMEMissingTransport is raised when transport file is empty."""
    monkeypatch.setattr('os.path.join', lambda *args: '/sys/class/nvme/nvme0/transport')
    monkeypatch.setattr('os.path.exists', lambda path: True)
    monkeypatch.setattr(
        'leapp.libraries.actor.scannvme.read_file',
        lambda path: '   \n'
    )

    with pytest.raises(scannvme.NVMEMissingTransport):
        scannvme._get_transport_type('/sys/class/nvme/nvme0')


@pytest.mark.parametrize('transport_value', ['pcie', 'tcp', 'rdma', 'fc', 'loop'])
def test_get_transport_type_valid(monkeypatch, transport_value):
    """Test that transport type is correctly read from the file."""
    monkeypatch.setattr('os.path.join', lambda *args: '/sys/class/nvme/nvme0/transport')
    monkeypatch.setattr('os.path.exists', lambda path: True)
    monkeypatch.setattr(scannvme, 'read_file', lambda path: transport_value + '\n')

    result = scannvme._get_transport_type('/sys/class/nvme/nvme0')
    assert result == transport_value


def test_scan_device_transport_detection_fails(monkeypatch):
    """Test that None is returned when transport detection fails."""
    monkeypatch.setattr('os.path.join', lambda *args: '/'.join(args))
    monkeypatch.setattr('os.path.isdir', lambda path: True)
    monkeypatch.setattr('os.path.exists', lambda path: False)

    result = scannvme.scan_device('nvme0')

    assert result is None


@pytest.mark.parametrize('device_name,transport', [
    ('nvme0', 'pcie'),
    ('nvme1', 'tcp'),
    ('nvme2', 'rdma'),
])
def test_scan_device_successful(monkeypatch, device_name, transport):
    """Test that NVMEDevice is returned for a valid device."""
    expected_device_path = '/sys/class/nvme/{}'.format(device_name)
    expected_transport_path = '{}/transport'.format(expected_device_path)

    def mock_isdir(path):
        assert path == expected_device_path
        return True

    def mock_exists(path):
        assert path == expected_transport_path
        return True

    def mock_read_file(path):
        assert path == expected_transport_path
        return transport + '\n'

    monkeypatch.setattr('os.path.join', lambda *args: '/'.join(args))
    monkeypatch.setattr('os.path.isdir', mock_isdir)
    monkeypatch.setattr('os.path.exists', mock_exists)
    monkeypatch.setattr(scannvme, 'read_file', mock_read_file)

    result = scannvme.scan_device(device_name)

    assert result is not None
    assert isinstance(result, NVMEDevice)
    assert result.name == device_name
    assert result.transport == transport
    assert result.sys_class_path == expected_device_path
