import functools
import os
import random

from leapp import models, reporting
from leapp.libraries import stdlib
from leapp.libraries.actor import vdoconversionscanner
from leapp.libraries.common.testutils import create_report_mocked


def aslist(f):
    """ Decorator used to convert generator to list """
    @functools.wraps(f)
    def inner(*args, **kwargs):
        return list(f(*args, **kwargs))
    return inner


def _lsblk_entry(prefix, number, types):
    return models.LsblkEntry(
        name='{0}{1}'.format(prefix, number),
        maj_min='253:{0}'.format(number),
        rm='0',
        size='100G',
        ro='0',
        tp=types[random.randint(0, len(types) - 1)],
        mountpoint='')


@aslist
def _lsblk_entries(pre=0, post=0, complete=0, undetermined=0):

    begin = pre
    for x in range(begin):
        yield _lsblk_entry('vdo_pre_', x, ['disk', 'part'])
    begin += pre

    for x in range(begin, begin + complete):
        yield _lsblk_entry('vdo_post_complete_', x, ['disk', 'part'])
    begin += complete

    for x in range(begin, begin + (post - complete)):
        yield _lsblk_entry('vdo_post_', x, ['disk', 'part'])
    begin += post - complete

    for x in range(begin, begin + undetermined):
        yield _lsblk_entry('vdo_undetermined_', x, ['disk', 'part'])


def _storage_info(pre=0, post=0, complete=0, undetermined=0):
    return models.StorageInfo(lsblk=_lsblk_entries(pre, post, complete, undetermined))


def _check_vdo_lvm_managed(device):
    device = os.path.split(device)[-1]
    code = 2
    if device.startswith('vdo_') and ("_post_" in device) and ("_complete_" in device):
        code = 0
    return code


def _check_vdo_pre_conversion(device):
    device = os.path.split(device)[-1]
    code = 255
    if device.startswith('vdo_'):
        code = -1 if '_undetermined_' in device else 1 if "_pre_" in device else 0
    return code


def test_check_vdo_pre_conversion(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(vdoconversionscanner, '_lvm_package_installed', lambda: True)
    monkeypatch.setattr(vdoconversionscanner, '_vdo_package_installed', lambda: True)
    monkeypatch.setattr(vdoconversionscanner, '_check_vdo_lvm_managed', _check_vdo_lvm_managed)

    monkeypatch.setattr(stdlib, 'run', lambda _, checked: {'exit_code': 0})
    info = vdoconversionscanner.get_info(_storage_info(pre=1))
    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion, list) and (not info.pre_conversion)
    assert isinstance(info.post_conversion, list) and (len(info.post_conversion) == 1)
    assert not info.post_conversion[0].complete
    assert isinstance(info.undetermined_conversion, list) and (not info.undetermined_conversion)

    monkeypatch.setattr(stdlib, 'run', lambda _, checked: {'exit_code': 1})
    info = vdoconversionscanner.get_info(_storage_info(pre=1))
    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion, list) and (len(info.pre_conversion) == 1)
    assert isinstance(info.post_conversion, list) and (not info.post_conversion)
    assert isinstance(info.undetermined_conversion, list) and (not info.undetermined_conversion)

    monkeypatch.setattr(stdlib, 'run', lambda _, checked: {'exit_code': 255})
    info = vdoconversionscanner.get_info(_storage_info(pre=1))
    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion, list) and (not info.pre_conversion)
    assert isinstance(info.post_conversion, list) and (not info.post_conversion)
    assert isinstance(info.undetermined_conversion, list) and (not info.undetermined_conversion)

    monkeypatch.setattr(stdlib, 'run', lambda _, checked: {'exit_code': -1})
    info = vdoconversionscanner.get_info(_storage_info(pre=1))
    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion, list) and (not info.pre_conversion)
    assert isinstance(info.post_conversion, list) and (not info.post_conversion)
    assert isinstance(info.undetermined_conversion, list) and (len(info.undetermined_conversion) == 1)


def test_check_vdo_lvm_managed(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(vdoconversionscanner, '_lvm_package_installed', lambda: True)
    monkeypatch.setattr(vdoconversionscanner, '_vdo_package_installed', lambda: True)
    monkeypatch.setattr(vdoconversionscanner, '_check_vdo_pre_conversion', _check_vdo_pre_conversion)

    monkeypatch.setattr(stdlib, 'run', lambda _, checked: {'exit_code': 0})
    info = vdoconversionscanner.get_info(_storage_info(post=1))
    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion, list) and (not info.pre_conversion)
    assert isinstance(info.post_conversion, list) and (len(info.post_conversion) == 1)
    assert info.post_conversion[0].complete
    assert not info.post_conversion[0].failure
    assert isinstance(info.undetermined_conversion, list) and (not info.undetermined_conversion)

    monkeypatch.setattr(stdlib, 'run', lambda _, checked: {'exit_code': 2})
    info = vdoconversionscanner.get_info(_storage_info(post=1))
    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion, list) and (not info.pre_conversion)
    assert isinstance(info.post_conversion, list) and (len(info.post_conversion) == 1)
    assert not info.post_conversion[0].complete
    assert not info.post_conversion[0].failure
    assert isinstance(info.undetermined_conversion, list) and (not info.undetermined_conversion)

    monkeypatch.setattr(stdlib, 'run', lambda _, checked: {'exit_code': -1})
    info = vdoconversionscanner.get_info(_storage_info(post=1))
    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion, list) and (not info.pre_conversion)
    assert isinstance(info.post_conversion, list) and (len(info.post_conversion) == 1)
    assert not info.post_conversion[0].complete
    assert info.post_conversion[0].failure
    assert isinstance(info.undetermined_conversion, list) and (not info.undetermined_conversion)


def test_lvm_package_not_installed(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(vdoconversionscanner, '_lvm_package_installed', lambda: False)
    monkeypatch.setattr(vdoconversionscanner, '_vdo_package_installed', lambda: False)
    monkeypatch.setattr(vdoconversionscanner, '_check_vdo_pre_conversion', _check_vdo_pre_conversion)
    monkeypatch.setattr(vdoconversionscanner, '_check_vdo_lvm_managed', _check_vdo_lvm_managed)

    pre = 0
    post = 0
    complete = 0
    undetermined = 5

    info = vdoconversionscanner.get_info(_storage_info(pre, post, complete, undetermined))

    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion, list) and (not info.pre_conversion)
    assert isinstance(info.post_conversion, list) and (not info.post_conversion)
    assert isinstance(info.undetermined_conversion, list) and (not info.undetermined_conversion)


def test_no_vdo_devices(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(vdoconversionscanner, '_lvm_package_installed', lambda: True)
    monkeypatch.setattr(vdoconversionscanner, '_vdo_package_installed', lambda: True)
    monkeypatch.setattr(vdoconversionscanner, '_check_vdo_pre_conversion', _check_vdo_pre_conversion)
    monkeypatch.setattr(vdoconversionscanner, '_check_vdo_lvm_managed', _check_vdo_lvm_managed)

    info = vdoconversionscanner.get_info(_storage_info())

    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion, list) and (not info.pre_conversion)
    assert isinstance(info.post_conversion, list) and (not info.post_conversion)
    assert isinstance(info.undetermined_conversion, list) and (not info.undetermined_conversion)


def test_vdo_devices(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(vdoconversionscanner, '_lvm_package_installed', lambda: True)
    monkeypatch.setattr(vdoconversionscanner, '_vdo_package_installed', lambda: True)
    monkeypatch.setattr(vdoconversionscanner, '_check_vdo_pre_conversion', _check_vdo_pre_conversion)
    monkeypatch.setattr(vdoconversionscanner, '_check_vdo_lvm_managed', _check_vdo_lvm_managed)

    pre = 5
    post = 7
    complete = 3
    undetermined = 2

    info = vdoconversionscanner.get_info(_storage_info(pre, post, complete, undetermined))

    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion, list) and (len(info.pre_conversion) == pre)
    assert isinstance(info.post_conversion, list) and (len(info.post_conversion) == post)
    assert len([x for x in info.post_conversion if x.complete]) == complete
    assert (isinstance(info.undetermined_conversion, list) and
            (len(info.undetermined_conversion) == undetermined))


def test_vdo_package_not_installed(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(vdoconversionscanner, '_lvm_package_installed', lambda: True)
    monkeypatch.setattr(vdoconversionscanner, '_vdo_package_installed', lambda: False)
    monkeypatch.setattr(vdoconversionscanner, '_check_vdo_pre_conversion', _check_vdo_pre_conversion)
    monkeypatch.setattr(vdoconversionscanner, '_check_vdo_lvm_managed', _check_vdo_lvm_managed)

    pre = 5
    post = 7
    complete = 3
    undetermined = 2

    info = vdoconversionscanner.get_info(_storage_info(pre, post, complete, undetermined))

    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion, list) and (not info.pre_conversion)
    assert isinstance(info.post_conversion, list) and (not info.post_conversion)
    assert (isinstance(info.undetermined_conversion, list) and
            (len(info.undetermined_conversion) == (pre + post + undetermined)))
