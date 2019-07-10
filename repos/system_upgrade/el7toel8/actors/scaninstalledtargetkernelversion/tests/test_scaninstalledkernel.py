from leapp.libraries import stdlib
from leapp.libraries.actor import scankernel
from leapp.libraries.stdlib import api

TARGET_KERNEL_VERSION = '1.2.3-4.el8.x86_64'
TARGET_KERNEL = 'kernel-{}'.format(TARGET_KERNEL_VERSION)
OLD_KERNEL = 'kernel-0.1.2-3.el7.x86_64'


def mocked_run_with_target_kernel(*args, **kwargs):
    return {'stdout': [TARGET_KERNEL, OLD_KERNEL]}


def mocked_run_without_target_kernel(*args, **kwargs):
    return {'stdout': [OLD_KERNEL]}


def test_scaninstalledkernel(monkeypatch):
    result = []
    monkeypatch.setattr(stdlib, 'run', mocked_run_with_target_kernel)
    monkeypatch.setattr(api, 'produce', result.append)
    scankernel.process()
    assert result and result[0].version == TARGET_KERNEL_VERSION


def test_scaninstalledkernel_missing(monkeypatch):
    result = []
    monkeypatch.setattr(stdlib, 'run', mocked_run_without_target_kernel)
    monkeypatch.setattr(api, 'produce', result.append)
    scankernel.process()
    assert not result
