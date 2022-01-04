import functools
import random

from leapp import reporting
from leapp.libraries.actor import checkvdo
from leapp.libraries.common.testutils import create_report_mocked
from leapp.models import VdoConversionInfo, VdoPostConversion, VdoPreConversion


def aslist(f):
    """ Decorator used to convert generator to list """
    @functools.wraps(f)
    def inner(*args, **kwargs):
        return list(f(*args, **kwargs))
    return inner


@aslist
def _post_conversion_vdos(count = 0, complete = 0, start_char = 'a'):
    complete = min(count, complete)
    for x in range(complete):
        yield VdoPostConversion(name = "sd{0}".format(chr(ord(start_char) + x)),
                                complete = True)
    for x in range(complete, count):
        yield VdoPostConversion(name = "sd{0}".format(chr(ord(start_char) + x)),
                                complete = False)


@aslist
def _pre_conversion_vdos(count = 0, start_char = 'a'):
    for x in range(count):
        yield VdoPreConversion(name = "sd{0}".format(chr(ord(start_char) + x)))


def test_both_conversion_vdos(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    post_count = random.randint(1, 10)
    post_complete = random.randint(0, post_count)
    pre_count = random.randint(0, 10)
    checkvdo.check_vdo(
        VdoConversionInfo(
            post_conversion_vdos = _post_conversion_vdos(post_count, post_complete),
            pre_conversion_vdos = _pre_conversion_vdos(pre_count,
                                                       start_char = chr(ord('a') + post_count))))
    assert reporting.create_report.called == (pre_count + (post_count - post_complete))
    if (pre_count > 0) or ((post_count - post_complete) > 0):
        assert 'inhibitor' in reporting.create_report.report_fields['flags']
    elif 'flags' in reporting.create_report.report_fields:
        assert 'inhibitor' not in reporting.create_report.report_fields['flags']


def test_no_vdos(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkvdo.check_vdo(
        VdoConversionInfo(post_conversion_vdos = _post_conversion_vdos(),
                          pre_conversion_vdos = _pre_conversion_vdos()))
    assert reporting.create_report.called == 0


def test_post_conversion_vdos(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    count = random.randint(1, 10)
    complete = random.randint(0, count)
    checkvdo.check_vdo(
        VdoConversionInfo(post_conversion_vdos = _post_conversion_vdos(count, complete),
                          pre_conversion_vdos = _pre_conversion_vdos()))
    assert reporting.create_report.called == (count - complete)
    if count > complete:
        assert 'inhibitor' in reporting.create_report.report_fields['flags']
    elif 'flags' in reporting.create_report.report_fields:
        assert 'inhibitor' not in reporting.create_report.report_fields['flags']


def test_pre_conversion_vdos(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    count = random.randint(1, 10)
    checkvdo.check_vdo(
        VdoConversionInfo(post_conversion_vdos = _post_conversion_vdos(),
                          pre_conversion_vdos = _pre_conversion_vdos(count)))
    assert reporting.create_report.called == count
    assert 'inhibitor' in reporting.create_report.report_fields['flags']
