import pytest

from leapp.libraries import stdlib
from leapp.libraries.actor import scankernel
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api

TARGET_KERNEL_VERSION = '1.2.3-4.el9.x86_64'
TARGET_RT_KERNEL_VERSION = '1.2.3-4.rt56.7.el9.x86_64'
TARGET_KERNEL = 'kernel-core-{}'.format(TARGET_KERNEL_VERSION)
TARGET_RT_KERNEL = 'kernel-rt-core-{}'.format(TARGET_RT_KERNEL_VERSION)
OLD_KERNEL = 'kernel-core-0.1.2-3.el8.x86_64'
OLD_RT_KERNEL = 'kernel-rt-core-0.1.2-3.rt4.5.el8.x86_64'


class MockedRun(object):

    def __init__(self, stdouts):
        # stdouts should be dict of list of strings: { str: [str1,str2,...]}
        self._stdouts = stdouts

    def __call__(self, *args, **kwargs):
        for key in ('kernel-core', 'kernel-rt-core'):
            if key in args[0]:
                return {'stdout': self._stdouts.get(key, [])}
        return {'stdout': []}


@pytest.mark.parametrize('is_rt,exp_version,stdouts', [
    (False, TARGET_KERNEL_VERSION, {'kernel-core': [OLD_KERNEL, TARGET_KERNEL]}),
    (False, TARGET_KERNEL_VERSION, {'kernel-core': [TARGET_KERNEL, OLD_KERNEL]}),
    (False, TARGET_KERNEL_VERSION, {
        'kernel-core': [TARGET_KERNEL, OLD_KERNEL],
        'kernel-rt-core': [TARGET_RT_KERNEL, OLD_RT_KERNEL],
    }),
    (True, TARGET_RT_KERNEL_VERSION, {
        'kernel-rt-core': [OLD_RT_KERNEL, TARGET_RT_KERNEL]
    }),
    (True, TARGET_RT_KERNEL_VERSION, {
        'kernel-rt-core': [TARGET_RT_KERNEL, OLD_RT_KERNEL]
    }),
    (True, TARGET_RT_KERNEL_VERSION, {
        'kernel-core': [TARGET_KERNEL, OLD_KERNEL],
        'kernel-rt-core': [TARGET_RT_KERNEL, OLD_RT_KERNEL],
    }),
])
def test_scaninstalledkernel(monkeypatch, is_rt, exp_version, stdouts):
    result = []
    old_kver = '0.1.2-3.rt4.5.el8.x86_64' if is_rt else 'kernel-core-0.1.2-3.el88x86_64'
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver='9.0', kernel=old_kver))
    monkeypatch.setattr(api, 'produce', result.append)
    monkeypatch.setattr(scankernel, 'run', MockedRun(stdouts))
    scankernel.process()
    assert len(result) == 1 and result[0].version == exp_version


def test_scaninstalledkernel_missing_rt(monkeypatch):
    result = []
    old_kver = '0.1.2-3.rt4.5.el8.x86_64'
    stdouts = {'kernel-core': [TARGET_KERNEL], 'kernel-rt-core': [OLD_RT_KERNEL]}
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver='9.0', kernel=old_kver))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'produce', result.append)
    monkeypatch.setattr(scankernel, 'run', MockedRun(stdouts))
    scankernel.process()
    assert api.current_logger.warnmsg
    assert len(result) == 1 and result[0].version == TARGET_KERNEL_VERSION


def test_scaninstalledkernel_missing(monkeypatch):
    result = []
    old_kver = '0.1.2-3.rt4.5.el8.x86_64'
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(kernel=old_kver))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'produce', result.append)
    monkeypatch.setattr(scankernel, 'run', MockedRun({}))
    scankernel.process()
    assert api.current_logger.warnmsg
    assert api.current_logger.errmsg
    assert not result
