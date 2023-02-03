import pytest

from leapp.libraries.actor import rocescanner
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.libraries.stdlib import CalledProcessError

NMCLI_CON_NIC1 = [
    'ens1: connected to ens1',
    '"Mellanox MT27710"',
    'ethernet (mlx5_core), 82:28:9B:1B:28:2C, hw, mtu 1500',
    'inet4 192.168.0.2/24',
    'route4 192.168.0.1/24',
    'inet6 fe80::d8c5:3a67:1abb:dcca/64',
    'route6 fe80::/64',
    ''
]

NMCLI_CON_NIC2 = [
    'eno2: connected to eno2',
    '"mellanox MT27710"',
    'ethernet (mlx5_core), 82:28:9B:1B:28:2C, hw, mtu 1500',
    'inet4 172.18.0.2/16',
    'route4 172.18.0.1/16',
    'inet6 fe80::d8c5:3a67:1abb:dcca/64',
    'route6 fe80::/64',
    ''
]

NMCLI_DISCON_NIC3 = [
    'ens3: disconnected',
    '"Mellanox MT27710"',
    'ethernet (mlx5_core), 82:28:9B:1B:28:2C, hw, mtu 1500',
    ''
]

NMCLI_CON_NIC4 = [
    'mellanox4: connecting',
    '"Mellanox MT27710"',
    'ethernet (mlx5_core), 82:28:9B:1B:28:2C, hw, mtu 1500',
    'inet4 192.168.0.1/16',
    'route4 192.168.0.1/16',
    'inet6 fe80::d8c5:3a67:1abb:dcca/64',
    'route6 fe80::/64',
    ''
]

NMCLI_CON_NIC5_NO_ROCE = [
    'ens5: connected to ens5',
    '"Red Hat Virtio"',
    'ethernet (mlx5_core), 82:28:9B:1B:28:2C, hw, mtu 1500',
    'inet4 192.168.0.1/16',
    'route4 192.168.0.1/16',
    'inet6 fe80::d8c5:3a67:1abb:dcca/64',
    'route6 fe80::/64',
    ''
]


@pytest.mark.parametrize('nmcli_stdout,expected', (
    ([], []),
    (NMCLI_CON_NIC5_NO_ROCE, []),
    # simple
    (NMCLI_CON_NIC1, [NMCLI_CON_NIC1[0]]),
    (NMCLI_CON_NIC2, [NMCLI_CON_NIC2[0]]),
    (NMCLI_CON_NIC4, [NMCLI_CON_NIC4[0]]),
    (NMCLI_DISCON_NIC3, [NMCLI_DISCON_NIC3[0]]),
    # multiple
    (
        NMCLI_CON_NIC1 + NMCLI_CON_NIC2,
        [NMCLI_CON_NIC1[0], NMCLI_CON_NIC2[0]]
    ),
    (
        NMCLI_CON_NIC1 + NMCLI_DISCON_NIC3,
        [NMCLI_CON_NIC1[0], NMCLI_DISCON_NIC3[0]]
    ),
    (
        NMCLI_CON_NIC5_NO_ROCE + NMCLI_CON_NIC2,
        [NMCLI_CON_NIC2[0]]
    ),
    (
        NMCLI_CON_NIC2 + NMCLI_CON_NIC5_NO_ROCE,
        [NMCLI_CON_NIC2[0]]
    ),
))
def test_get_roce_nics_lines(monkeypatch, nmcli_stdout, expected):
    def mocked_run(cmd, *args, **kwargs):
        assert cmd == ['nmcli']
        return {'stdout': nmcli_stdout}
    monkeypatch.setattr(rocescanner, 'run', mocked_run)
    assert rocescanner.get_roce_nics_lines() == expected


@pytest.mark.parametrize('raise_exc', (
    CalledProcessError('foo', {'stdout': '', 'stderr': 'err', 'exit_code': '1'}, ['nmcli']),
    OSError('foo')
))
def test_get_roce_nics_lines_err(monkeypatch, raise_exc):
    def mocked_run(cmd, *args, **kwargs):
        assert cmd == ['nmcli']
        raise raise_exc
    monkeypatch.setattr(rocescanner, 'run', mocked_run)
    monkeypatch.setattr(rocescanner.api, 'current_logger', logger_mocked())
    monkeypatch.setattr(rocescanner.api, 'current_actor', CurrentActorMocked())
    assert rocescanner.get_roce_nics_lines() == []
    assert rocescanner.api.current_logger.warnmsg


@pytest.mark.parametrize('roce_lines,connected,connecting', (
    ([], [], []),
    ([NMCLI_DISCON_NIC3[0]], [], []),
    ([NMCLI_CON_NIC1[0]], ['ens1'], []),
    ([NMCLI_CON_NIC2[0]], ['eno2'], []),
    ([NMCLI_CON_NIC4[0]], [], ['mellanox4']),
    (
        [
            'ens1: connected to ens1',
            'eno2: connecting',
            'route6 fe80::/64',
            '',
            'ens3: connected to ens3',
        ],
        ['ens1', 'ens3'],
        ['eno2']
    ),
))
def test_roce_detected(monkeypatch, roce_lines, connected, connecting):
    mocked_produce = produce_mocked()
    monkeypatch.setattr(rocescanner.api, 'current_actor', CurrentActorMocked(arch=architecture.ARCH_S390X))
    monkeypatch.setattr(rocescanner.api.current_actor(), 'produce', mocked_produce)
    monkeypatch.setattr(rocescanner, 'get_roce_nics_lines', lambda: roce_lines)
    rocescanner.process()
    if connected or connecting:
        assert mocked_produce.called
        msg = mocked_produce.model_instances[0]
        assert msg.roce_nics_connected == connected
        assert msg.roce_nics_connecting == connecting
    else:
        assert not mocked_produce.called


@pytest.mark.parametrize('arch', (
    architecture.ARCH_ARM64,
    architecture.ARCH_X86_64,
    architecture.ARCH_PPC64LE
))
def test_roce_noibmz(monkeypatch, arch):
    def mocked_roce_lines():
        assert False, 'Unexpected call of get_roce_nics_lines on nonIBMz arch.'
    mocked_produce = produce_mocked()
    monkeypatch.setattr(rocescanner.api, 'current_actor', CurrentActorMocked(arch=arch))
    monkeypatch.setattr(rocescanner.api.current_actor(), 'produce', mocked_produce)
    monkeypatch.setattr(rocescanner, 'get_roce_nics_lines', lambda: mocked_roce_lines)
    assert not mocked_produce.called
