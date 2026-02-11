import pytest

from leapp.libraries.actor import emit_net_naming as emit_net_naming_lib
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    KernelCmdline,
    KernelCmdlineArg,
    RpmTransactionTasks,
    TargetKernelCmdlineArgTasks,
    TargetUserSpaceUpgradeTasks,
    UpgradeKernelCmdlineArgTasks
)


@pytest.mark.parametrize(
    ('kernel_args', 'should_be_compatible'),
    [
        ([KernelCmdlineArg(key='net.naming-scheme', value='rhel-8.10')], False),
        ([KernelCmdlineArg(key='net.ifnames', value='1')], True),
        ([KernelCmdlineArg(key='net.ifnames', value='0')], False),
        (
            [
                KernelCmdlineArg(key='net.naming-scheme', value='rhel-8.10'),
                KernelCmdlineArg(key='net.ifname', value='0'),
                KernelCmdlineArg(key='root', value='/dev/vda1')
            ],
            False
        ),
        ([KernelCmdlineArg(key='root', value='/dev/vda1')], True),
    ]
)
def test_is_net_scheme_compatible_with_current_cmdline(monkeypatch, kernel_args, should_be_compatible):
    kernel_cmdline = KernelCmdline(parameters=kernel_args)

    def mocked_consume(msg_type):
        yield {KernelCmdline: kernel_cmdline}[msg_type]

    monkeypatch.setattr(api, 'consume', mocked_consume)

    assert emit_net_naming_lib.is_net_scheme_compatible_with_current_cmdline() == should_be_compatible, \
        [(arg.key, arg.value) for arg in kernel_cmdline.parameters]


@pytest.mark.parametrize(
    ('is_net_scheme_enabled', 'is_current_cmdline_compatible'),
    [
        (True, True),
        (True, False),
        (False, True)
    ]
)
@pytest.mark.parametrize(
    'source_ver, target_ver',
    [
        ('8.10', '9.5'),
        ('8.10', '9.8'),
        ('9.6', '10.0'),
        ('9.8', '10.2'),
    ]
)
@pytest.mark.parametrize('target_distro', ['rhel', 'centos'])
def test_emit_msgs_to_use_net_naming_schemes(
    monkeypatch,
    is_net_scheme_enabled,
    is_current_cmdline_compatible,
    source_ver,
    target_ver,
    target_distro,
):
    mocked_actor = CurrentActorMocked(
        src_ver=source_ver,
        dst_ver=target_ver,
        dst_distro=target_distro,
        envars={
            "LEAPP_DISABLE_NET_NAMING_SCHEMES": "0" if is_net_scheme_enabled else "1"
        },
    )
    monkeypatch.setattr(api, 'current_actor', mocked_actor)

    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(emit_net_naming_lib,
                        'is_net_scheme_compatible_with_current_cmdline',
                        lambda: is_current_cmdline_compatible)

    emit_net_naming_lib.emit_msgs_to_use_net_naming_schemes()

    def ensure_one_msg_of_type_produced(produced_messages, msg_type):
        msgs = (msg for msg in produced_messages if isinstance(msg, msg_type))
        msg = next(msgs)
        assert not next(msgs, None), 'More than one message of type {type} produced'.format(type=type)
        return msg

    target_major = target_ver.split(".")[0]
    pkg_name = emit_net_naming_lib.NET_NAMING_SYSATTRS_RPM_NAME[target_major]
    produced_messages = api.produce.model_instances

    # the package is available since 10.2
    if is_net_scheme_enabled and target_ver != "10.0":
        userspace_tasks = ensure_one_msg_of_type_produced(produced_messages, TargetUserSpaceUpgradeTasks)
        assert userspace_tasks.install_rpms == [pkg_name]

        rpm_tasks = ensure_one_msg_of_type_produced(produced_messages, RpmTransactionTasks)
        assert rpm_tasks.to_install == [pkg_name]
    else:
        assert not api.produce.called
        return

    upgrade_cmdline_mods = (msg for msg in produced_messages if isinstance(msg, UpgradeKernelCmdlineArgTasks))
    target_cmdline_mods = (msg for msg in produced_messages if isinstance(msg, TargetKernelCmdlineArgTasks))

    if is_current_cmdline_compatible:
        # We should emit cmdline modifications - both UpgradeKernelCmdlineArgTasks and TargetKernelCmdlineArgTasks
        # should be produced
        assert next(upgrade_cmdline_mods, None)
        assert next(target_cmdline_mods, None)
    else:
        assert not next(upgrade_cmdline_mods, None)
        assert not next(target_cmdline_mods, None)
