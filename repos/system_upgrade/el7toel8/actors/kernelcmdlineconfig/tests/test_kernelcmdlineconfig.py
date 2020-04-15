from collections import namedtuple

from leapp.libraries import stdlib
from leapp.libraries.actor import kernelcmdlineconfig
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import InstalledTargetKernelVersion, KernelCmdlineArg

KERNEL_VERSION = '1.2.3-4.x86_64.el8'


class MockedRun(object):
    def __init__(self):
        self.commands = []

    def __call__(self, cmd, *args, **kwargs):
        self.commands.append(cmd)
        return {}


def mocked_consume(*models):
    if InstalledTargetKernelVersion in models:
        return iter((InstalledTargetKernelVersion(version=KERNEL_VERSION),))
    return iter((
        KernelCmdlineArg(key='some_key1', value='some_value1'),
        KernelCmdlineArg(key='some_key2', value='some_value2')
    ))


def mocked_consume_no_args(*models):
    if InstalledTargetKernelVersion in models:
        return iter((InstalledTargetKernelVersion(version=KERNEL_VERSION),))
    return iter(())


def mocked_consume_no_version(*models):
    if InstalledTargetKernelVersion in models:
        return iter(())
    assert False and 'this should not be called'
    return iter(())


def test_kernelcmdline_config_intel(monkeypatch):
    mocked_run = MockedRun()
    monkeypatch.setattr(stdlib, 'run', mocked_run)
    monkeypatch.setattr(api, 'consume', mocked_consume)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_X86_64))
    kernelcmdlineconfig.process()
    assert mocked_run.commands and len(mocked_run.commands) == 2
    assert ['grubby', '--update-kernel=/boot/vmlinuz-{}'.format(
        KERNEL_VERSION), '--args=some_key2=some_value2'] == mocked_run.commands.pop()
    assert ['grubby', '--update-kernel=/boot/vmlinuz-{}'.format(
        KERNEL_VERSION), '--args=some_key1=some_value1'] == mocked_run.commands.pop()


def test_kernelcmdline_config_ibmz(monkeypatch):
    mocked_run = MockedRun()
    monkeypatch.setattr(stdlib, 'run', mocked_run)
    monkeypatch.setattr(api, 'consume', mocked_consume)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_S390X))
    kernelcmdlineconfig.process()
    assert mocked_run.commands and len(mocked_run.commands) == 4
    assert ['grubby', '--update-kernel=/boot/vmlinuz-{}'.format(
        KERNEL_VERSION), '--args=some_key1=some_value1'] == mocked_run.commands.pop(0)
    assert ['/usr/sbin/zipl'] == mocked_run.commands.pop(0)
    assert ['grubby', '--update-kernel=/boot/vmlinuz-{}'.format(
        KERNEL_VERSION), '--args=some_key2=some_value2'] == mocked_run.commands.pop(0)
    assert ['/usr/sbin/zipl'] == mocked_run.commands.pop(0)


def test_kernelcmdline_config_no_args(monkeypatch):
    mocked_run = MockedRun()
    monkeypatch.setattr(stdlib, 'run', mocked_run)
    monkeypatch.setattr(api, 'consume', mocked_consume_no_args)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_S390X))
    kernelcmdlineconfig.process()
    assert not mocked_run.commands


def test_kernelcmdline_config_no_version(monkeypatch):
    mocked_run = MockedRun()
    monkeypatch.setattr(stdlib, 'run', mocked_run)
    monkeypatch.setattr(api, 'consume', mocked_consume_no_version)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_S390X))
    kernelcmdlineconfig.process()
    assert not mocked_run.commands
