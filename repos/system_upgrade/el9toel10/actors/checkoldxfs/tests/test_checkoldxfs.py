import pytest

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import checkoldxfs
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    XFSInfo,
    XFSInfoData,
    XFSInfoFacts,
    XFSInfoLog,
    XFSInfoMetaData,
    XFSInfoNaming,
    XFSInfoRealtime
)
from leapp.utils.report import is_inhibitor


def test_has_valid_bigtime_passes():
    """
    Test _has_valid_bigtime passes for correct attributes.
    """

    xfs_info = XFSInfo(
        mountpoint='/MOUNTPOINT',
        meta_data=XFSInfoMetaData(bigtime='1', crc=None, device='/dev/vda'),
        data=XFSInfoData(blocks='524288', bsize='4096'),
        naming=XFSInfoNaming(),
        log=XFSInfoLog(blocks='2560', bsize='4096'),
        realtime=XFSInfoRealtime(),
    )

    assert checkoldxfs._has_valid_bigtime(xfs_info)


@pytest.mark.parametrize("bigtime", ['0', '', '<UNKNOWN>', None])
def test_has_valid_bigtime_fail(bigtime):
    """
    Test _has_valid_bigtime fails for incorrect attributes.
    """

    xfs_info = XFSInfo(
        mountpoint='/MOUNTPOINT',
        meta_data=(
            XFSInfoMetaData(bigtime=bigtime, crc=None, device='/dev/vda')
            if bigtime
            else XFSInfoMetaData(device='/dev/vda')
        ),
        data=XFSInfoData(blocks='524288', bsize='4096'),
        naming=XFSInfoNaming(),
        log=XFSInfoLog(blocks='2560', bsize='4096'),
        realtime=XFSInfoRealtime(),
    )

    assert not checkoldxfs._has_valid_bigtime(xfs_info)


def test_has_valid_crc_passes():
    """
    Test _has_valid_crc passes for correct attributes.
    """

    xfs_info = XFSInfo(
        mountpoint='/MOUNTPOINT',
        meta_data=XFSInfoMetaData(crc='1', bigtime=None, device='/dev/vda'),
        data=XFSInfoData(blocks='524288', bsize='4096'),
        naming=XFSInfoNaming(),
        log=XFSInfoLog(blocks='2560', bsize='4096'),
        realtime=XFSInfoRealtime(),
    )

    assert checkoldxfs._has_valid_crc(xfs_info)


@pytest.mark.parametrize("crc", ['0', '', '<UNKNOWN>', None])
def test_has_valid_crc_fail(crc):
    """
    Test _has_valid_crc fails for incorrect attributes.
    """

    xfs_info = XFSInfo(
        mountpoint='/MOUNTPOINT',
        meta_data=(
            XFSInfoMetaData(crc=crc, bigtime=None, device='/dev/vda')
            if crc
            else XFSInfoMetaData(device='/dev/vda')
        ),
        data=XFSInfoData(blocks='524288', bsize='4096'),
        naming=XFSInfoNaming(),
        log=XFSInfoLog(blocks='2560', bsize='4096'),
        realtime=XFSInfoRealtime(),
    )

    assert not checkoldxfs._has_valid_crc(xfs_info)


def test_get_xfs_info_facts_info_single_entry(monkeypatch):
    xfs_info_facts = XFSInfoFacts(mountpoints=[])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[xfs_info_facts]))

    result = checkoldxfs._get_xfs_info_facts()
    assert result == xfs_info_facts


def test_get_workaround_efi_info_multiple_entries(monkeypatch):
    logger = logger_mocked()
    xfs_info_facts = XFSInfoFacts(mountpoints=[])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=[xfs_info_facts, xfs_info_facts]))
    monkeypatch.setattr(api, 'current_logger', logger)

    result = checkoldxfs._get_xfs_info_facts()
    assert result == xfs_info_facts
    assert 'Unexpectedly received more than one XFSInfoFacts message.' in logger.warnmsg


def test_get_workaround_efi_info_no_entry(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[]))

    with pytest.raises(StopActorExecutionError, match='Could not retrieve XFSInfoFacts!'):
        checkoldxfs._get_xfs_info_facts()


def test_valid_xfs_passes(monkeypatch):
    """
    Test no report is generated for valid XFS mountpoint
    """

    logger = logger_mocked()
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[
        XFSInfoFacts(
            mountpoints=[
                XFSInfo(
                    mountpoint='/MOUNTPOINT',
                    meta_data=XFSInfoMetaData(crc='1', bigtime='1', device='/dev/vda'),
                    data=XFSInfoData(blocks='524288', bsize='4096'),
                    naming=XFSInfoNaming(),
                    log=XFSInfoLog(blocks='2560', bsize='4096'),
                    realtime=XFSInfoRealtime(),
                ),
            ]
        )
    ]))

    checkoldxfs.process()

    assert 'All XFS system detected are valid.' in logger.dbgmsg[0]
    assert not reporting.create_report.called


@pytest.mark.parametrize(
    'valid_crc,valid_bigtime',
    [
        (False, True),
        (True, False),
        (False, False),
    ]
)
def test_unsupported_xfs(monkeypatch, valid_crc, valid_bigtime):
    """
    Test report is generated for unsupported XFS mountpoint
    """

    logger = logger_mocked()
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[
        XFSInfoFacts(
            mountpoints=[
                XFSInfo(
                    mountpoint='/MOUNTPOINT',
                    meta_data=XFSInfoMetaData(
                        crc='1' if valid_crc else '0',
                        bigtime='1' if valid_bigtime else '0',
                        device='/dev/vda',
                    ),
                    data=XFSInfoData(blocks='524288', bsize='4096'),
                    naming=XFSInfoNaming(),
                    log=XFSInfoLog(blocks='2560', bsize='4096'),
                    realtime=XFSInfoRealtime(),
                ),
            ]
        )
    ]))

    checkoldxfs.process()

    assert reporting.create_report.called == (int(not valid_crc) + int(not valid_bigtime))

    if not valid_crc:
        reports = [
            report
            for report in reporting.create_report.reports
            if report.get('title') == 'Detected XFS filesystems incompatible with target kernel.'
        ]
        assert reports
        report = reports[-1]
        assert 'XFS v4 format has been deprecated' in report.get('summary')
        assert report['severity'] == reporting.Severity.HIGH
        assert is_inhibitor(report)

    if not valid_bigtime:
        reports = [
            report
            for report in reporting.create_report.reports
            if report.get('title') == 'Detected XFS filesystems without bigtime feature.'
        ]
        assert reports
        report = reports[-1]
        assert 'XFS v5 filesystem format introduced the "bigtime" feature' in report.get('summary')
        assert report['severity'] == reporting.Severity.LOW
