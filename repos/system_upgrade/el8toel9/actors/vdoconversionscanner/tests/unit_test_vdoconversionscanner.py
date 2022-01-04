import functools
import os
import random

from leapp import models, reporting
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
        name = '{0}{1}'.format(prefix, number),
        maj_min = '253:{0}'.format(number),
        rm = '0',
        size = '100G',
        ro = '0',
        tp = types[random.randint(0, len(types) - 1)],
        mountpoint = '')

@aslist
def _lsblk_entries(pre = 0, post = 0, complete = 0):
    complete = min(post, complete)

    begin = pre
    for x in range(begin):
        yield _lsblk_entry('vdo_pre_', x, ['disk', 'part'])
    begin += pre

    for x in range(begin, begin + complete):
        yield _lsblk_entry('vdo_post_complete_', x, ['disk', 'part'])
    begin += complete

    for x in range(begin, begin + (post - complete)):
        yield _lsblk_entry('vdo_post_', x, ['disk', 'part'])


def _storage_info(pre = 0, post = 0, complete = 0):
    return models.StorageInfo(lsblk = _lsblk_entries(pre, post, complete))


def _is_vdo_lvm_managed(device):
    device = os.path.split(device)[-1]
    return device.startswith('vdo_') and ("_post_" in device) and ("_complete_" in device)


def _get_vdo_pre_conversion(device):
    device = os.path.split(device)[-1]
    code = 255
    if device.startswith('vdo_'):
        code = 1 if "_pre_" in device else 0
    return code


def test_get_vdo_pre_conversion(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(vdoconversionscanner, '_required_packages_not_installed', lambda: [])
    monkeypatch.setattr(vdoconversionscanner, '_is_vdo_lvm_managed', _is_vdo_lvm_managed)

    monkeypatch.setattr(vdoconversionscanner, '_run_cmd', lambda _,checked: {'exit_code': 0})
    info = vdoconversionscanner.get_info(_storage_info(pre = 1))
    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion_vdos, list) and (not info.pre_conversion_vdos)
    assert isinstance(info.post_conversion_vdos, list) and (len(info.post_conversion_vdos) == 1)
    assert not info.post_conversion_vdos[0].complete
    assert reporting.create_report.called == 0

    monkeypatch.setattr(vdoconversionscanner, '_run_cmd', lambda _,checked: {'exit_code': 1})
    info = vdoconversionscanner.get_info(_storage_info(pre = 1))
    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion_vdos, list) and (len(info.pre_conversion_vdos) == 1)
    assert isinstance(info.post_conversion_vdos, list) and (not info.post_conversion_vdos)
    assert reporting.create_report.called == 0

    monkeypatch.setattr(vdoconversionscanner, '_run_cmd', lambda _,checked: {'exit_code': 255})
    info = vdoconversionscanner.get_info(_storage_info(pre = 1))
    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion_vdos, list) and (not info.pre_conversion_vdos)
    assert isinstance(info.post_conversion_vdos, list) and (not info.post_conversion_vdos)
    assert reporting.create_report.called == 0

    monkeypatch.setattr(vdoconversionscanner, '_run_cmd', lambda _,checked: {'exit_code': -1})
    info = vdoconversionscanner.get_info(_storage_info(pre = 1))
    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion_vdos, list) and (not info.pre_conversion_vdos)
    assert isinstance(info.post_conversion_vdos, list) and (not info.post_conversion_vdos)
    assert reporting.create_report.called == 1


def test_is_vdo_lvm_managed(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(vdoconversionscanner, '_required_packages_not_installed', lambda: [])
    monkeypatch.setattr(vdoconversionscanner, '_get_vdo_pre_conversion', _get_vdo_pre_conversion)

    monkeypatch.setattr(vdoconversionscanner, '_run_cmd', lambda _,checked: {'exit_code': 0})
    info = vdoconversionscanner.get_info(_storage_info(post = 1))
    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion_vdos, list) and (not info.pre_conversion_vdos)
    assert isinstance(info.post_conversion_vdos, list) and (len(info.post_conversion_vdos) == 1)
    assert info.post_conversion_vdos[0].complete
    assert reporting.create_report.called == 0

    monkeypatch.setattr(vdoconversionscanner, '_run_cmd', lambda _,checked: {'exit_code': 2})
    info = vdoconversionscanner.get_info(_storage_info(post = 1))
    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion_vdos, list) and (not info.pre_conversion_vdos)
    assert isinstance(info.post_conversion_vdos, list) and (len(info.post_conversion_vdos) == 1)
    assert not info.post_conversion_vdos[0].complete
    assert reporting.create_report.called == 0

    monkeypatch.setattr(vdoconversionscanner, '_run_cmd', lambda _,checked: {'exit_code': -1})
    info = vdoconversionscanner.get_info(_storage_info(post = 1))
    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion_vdos, list) and (not info.pre_conversion_vdos)
    assert isinstance(info.post_conversion_vdos, list) and (len(info.post_conversion_vdos) == 1)
    assert not info.post_conversion_vdos[0].complete
    assert reporting.create_report.called == 1


def test_no_vdo_devices(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(vdoconversionscanner, '_required_packages_not_installed', lambda: [])
    monkeypatch.setattr(vdoconversionscanner, '_get_vdo_pre_conversion', _get_vdo_pre_conversion)
    monkeypatch.setattr(vdoconversionscanner, '_is_vdo_lvm_managed', _is_vdo_lvm_managed)

    info = vdoconversionscanner.get_info(_storage_info())

    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion_vdos, list) and (not info.pre_conversion_vdos)
    assert isinstance(info.pre_conversion_vdos, list) and (not info.post_conversion_vdos)
    assert reporting.create_report.called == 0


def test_vdo_devices(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(vdoconversionscanner, '_required_packages_not_installed', lambda: [])
    monkeypatch.setattr(vdoconversionscanner, '_get_vdo_pre_conversion', _get_vdo_pre_conversion)
    monkeypatch.setattr(vdoconversionscanner, '_is_vdo_lvm_managed', _is_vdo_lvm_managed)

    pre = random.randint(1, 10)
    post = random.randint(1, 10)
    complete = random.randint(0, post)

    info = vdoconversionscanner.get_info(_storage_info(pre, post, complete))

    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion_vdos, list) and (len(info.pre_conversion_vdos) == pre)
    assert isinstance(info.pre_conversion_vdos, list) and (len(info.post_conversion_vdos) == post)
    assert len([x for x in info.post_conversion_vdos if x.complete]) == complete
    assert reporting.create_report.called == 0


def test_required_vdo_package_not_installed(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(vdoconversionscanner, '_required_packages_not_installed', lambda: ['vdo'])
    monkeypatch.setattr(vdoconversionscanner, '_get_vdo_pre_conversion', _get_vdo_pre_conversion)
    monkeypatch.setattr(vdoconversionscanner, '_is_vdo_lvm_managed', _is_vdo_lvm_managed)

    info = vdoconversionscanner.get_info(_storage_info())

    assert isinstance(info, models.VdoConversionInfo)
    assert isinstance(info.pre_conversion_vdos, list) and (not info.pre_conversion_vdos)
    assert isinstance(info.pre_conversion_vdos, list) and (not info.post_conversion_vdos)
    assert reporting.create_report.called == 1
    assert 'package(s) required for upgrade validation check' in reporting.create_report.report_fields['summary']
    assert 'inhibitor' in reporting.create_report.report_fields['flags']
