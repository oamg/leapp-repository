import functools

from leapp import reporting
from leapp.libraries.actor import checkvdo
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import (
    VdoConversionInfo,
    VdoConversionPostDevice,
    VdoConversionPreDevice,
    VdoConversionUndeterminedDevice
)
from leapp.utils.report import is_inhibitor


class MockedActorNoVdoDevices(CurrentActorMocked):
    def get_no_vdo_devices_response(self):
        return True


class MockedActorSomeVdoDevices(CurrentActorMocked):
    def get_no_vdo_devices_response(self):
        return False


def aslist(f):
    """ Decorator used to convert generator to list """
    @functools.wraps(f)
    def inner(*args, **kwargs):
        return list(f(*args, **kwargs))
    return inner


@aslist
def _post_conversion_vdos(count=0, complete=0, failing=0, start_char='a'):
    begin = complete
    for x in range(begin):
        yield VdoConversionPostDevice(name='sd{0}'.format(chr(ord(start_char) + x)),
                                      complete=True)

    for x in range(begin, begin + failing):
        yield VdoConversionPostDevice(name='sd{0}'.format(chr(ord(start_char) + x)),
                                      complete=False,
                                      check_failed=True,
                                      failure='unit testing')
    begin += failing

    for x in range(begin, count):
        yield VdoConversionPostDevice(name='sd{0}'.format(chr(ord(start_char) + x)),
                                      complete=False)


@aslist
def _pre_conversion_vdos(count=0, start_char='a'):
    for x in range(count):
        yield VdoConversionPreDevice(name='sd{0}'.format(chr(ord(start_char) + x)))


@aslist
def _undetermined_conversion_vdos(count=0, failing=False, start_char='a'):
    for x in range(count):
        yield VdoConversionUndeterminedDevice(name='sd{0}'.format(chr(ord(start_char) + x)),
                                              check_failed=failing,
                                              failure='unit testing' if failing else None)


# No VDOs tests.
def test_no_vdos(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkvdo.check_vdo(
        VdoConversionInfo(post_conversion=_post_conversion_vdos(),
                          pre_conversion=_pre_conversion_vdos(),
                          undetermined_conversion=_undetermined_conversion_vdos()))
    assert reporting.create_report.called == 0


# Concurrent pre- and post-conversion tests.
def test_both_conversion_vdo_incomplete(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    post_count = 7
    checkvdo.check_vdo(
        VdoConversionInfo(
            post_conversion=_post_conversion_vdos(post_count, 5),
            pre_conversion=_pre_conversion_vdos(3, start_char=chr(ord('a') + post_count)),
            undetermined_conversion=_undetermined_conversion_vdos()))
    assert reporting.create_report.called == 2
    assert is_inhibitor(reporting.create_report.report_fields)


# Post-conversion tests.
def test_post_conversion_multiple_vdo_incomplete(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkvdo.check_vdo(
        VdoConversionInfo(post_conversion=_post_conversion_vdos(7, 5),
                          pre_conversion=_pre_conversion_vdos(),
                          undetermined_conversion=_undetermined_conversion_vdos()))
    assert reporting.create_report.called == 1
    assert is_inhibitor(reporting.create_report.report_fields)
    assert reporting.create_report.report_fields['summary'].startswith('VDO devices')


def test_post_conversion_multiple_vdo_complete(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkvdo.check_vdo(
        VdoConversionInfo(post_conversion=_post_conversion_vdos(7, 7),
                          pre_conversion=_pre_conversion_vdos(),
                          undetermined_conversion=_undetermined_conversion_vdos()))
    assert reporting.create_report.called == 0


def test_post_conversion_single_vdo_incomplete(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkvdo.check_vdo(
        VdoConversionInfo(post_conversion=_post_conversion_vdos(1),
                          pre_conversion=_pre_conversion_vdos(),
                          undetermined_conversion=_undetermined_conversion_vdos()))
    assert reporting.create_report.called == 1
    assert is_inhibitor(reporting.create_report.report_fields)
    assert (reporting.create_report.report_fields['summary'].startswith('VDO device')
            and (not reporting.create_report.report_fields['summary'].startswith('VDO devices')))


def test_post_conversion_single_check_failing(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkvdo.check_vdo(
        VdoConversionInfo(post_conversion=_post_conversion_vdos(2, complete=1, failing=1),
                          pre_conversion=_pre_conversion_vdos(),
                          undetermined_conversion=_undetermined_conversion_vdos()))
    assert reporting.create_report.called == 1
    assert is_inhibitor(reporting.create_report.report_fields)
    assert (reporting.create_report.report_fields['summary'].startswith(
            'Unexpected result checking device') and
            (not reporting.create_report.report_fields['summary'].startswith(
             'Unexpected result checking devices')))


def test_post_conversion_multiple_check_failing(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkvdo.check_vdo(
        VdoConversionInfo(post_conversion=_post_conversion_vdos(7, complete=4, failing=3),
                          pre_conversion=_pre_conversion_vdos(),
                          undetermined_conversion=_undetermined_conversion_vdos()))
    assert reporting.create_report.called == 1
    assert is_inhibitor(reporting.create_report.report_fields)
    assert reporting.create_report.report_fields['summary'].startswith(
            'Unexpected result checking devices')


def test_post_conversion_incomplete_and_check_failing(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkvdo.check_vdo(
        VdoConversionInfo(post_conversion=_post_conversion_vdos(2, failing=1),
                          pre_conversion=_pre_conversion_vdos(),
                          undetermined_conversion=_undetermined_conversion_vdos()))
    assert reporting.create_report.called == 2
    assert is_inhibitor(reporting.create_report.report_fields)


# Pre-conversion tests.
def test_pre_conversion_multiple_vdo_incomplete(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkvdo.check_vdo(
        VdoConversionInfo(post_conversion=_post_conversion_vdos(),
                          pre_conversion=_pre_conversion_vdos(7),
                          undetermined_conversion=_undetermined_conversion_vdos()))
    assert reporting.create_report.called == 1
    assert is_inhibitor(reporting.create_report.report_fields)
    assert reporting.create_report.report_fields['summary'].startswith('VDO devices')


def test_pre_conversion_single_vdo_incomplete(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkvdo.check_vdo(
        VdoConversionInfo(post_conversion=_post_conversion_vdos(),
                          pre_conversion=_pre_conversion_vdos(1),
                          undetermined_conversion=_undetermined_conversion_vdos()))
    assert reporting.create_report.called == 1
    assert is_inhibitor(reporting.create_report.report_fields)
    assert (reporting.create_report.report_fields['summary'].startswith('VDO device')
            and (not reporting.create_report.report_fields['summary'].startswith('VDO devices')))


# Undetermined tests.
def test_undetermined_single_check_failing(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkvdo.check_vdo(
        VdoConversionInfo(post_conversion=_post_conversion_vdos(),
                          pre_conversion=_pre_conversion_vdos(),
                          undetermined_conversion=_undetermined_conversion_vdos(1, True)))
    assert reporting.create_report.called == 1
    assert is_inhibitor(reporting.create_report.report_fields)
    assert (reporting.create_report.report_fields['summary'].startswith(
            'Unexpected result checking device') and
            (not reporting.create_report.report_fields['summary'].startswith(
             'Unexpected result checking devices')))


def test_undetermined_multiple_check_failing(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkvdo.check_vdo(
        VdoConversionInfo(post_conversion=_post_conversion_vdos(),
                          pre_conversion=_pre_conversion_vdos(),
                          undetermined_conversion=_undetermined_conversion_vdos(3, failing=True)))
    assert reporting.create_report.called == 1
    assert is_inhibitor(reporting.create_report.report_fields)
    assert reporting.create_report.report_fields['summary'].startswith(
            'Unexpected result checking devices')


def test_undetermined_multiple_no_check_no_vdos(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', MockedActorNoVdoDevices())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkvdo.check_vdo(
        VdoConversionInfo(post_conversion=_post_conversion_vdos(),
                          pre_conversion=_pre_conversion_vdos(),
                          undetermined_conversion=_undetermined_conversion_vdos(3)))
    assert reporting.create_report.called == 1
    assert not is_inhibitor(reporting.create_report.report_fields)
    assert reporting.create_report.report_fields['summary'].startswith(
            'User has asserted there are no VDO devices')


def test_undetermined_multiple_no_check_some_vdos(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', MockedActorSomeVdoDevices())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkvdo.check_vdo(
        VdoConversionInfo(post_conversion=_post_conversion_vdos(),
                          pre_conversion=_pre_conversion_vdos(),
                          undetermined_conversion=_undetermined_conversion_vdos(3)))
    assert reporting.create_report.called == 1
    assert is_inhibitor(reporting.create_report.report_fields)
    assert reporting.create_report.report_fields['summary'].startswith(
            'User has opted to inhibit upgrade')
