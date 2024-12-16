import pytest

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import checkoldxfs
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import XFSInfo, XFSInfoFacts
from leapp.utils.report import is_inhibitor


def test_has_valid_bigtime_passes():
    """
    Test _has_valid_bigtime passes for correct attributes.
    """

    xfs_info = XFSInfo(
        mountpoint='/MOUNTPOINT',
        meta_data={'bigtime': '1'},
        data={},
        naming={},
        log={},
        realtime={},
    )

    assert checkoldxfs._has_valid_bigtime(xfs_info)


@pytest.mark.parametrize("bigtime", ['0', '', '<UNKNOWN>', None])
def test_has_valid_bigtime_fail(bigtime):
    """
    Test _has_valid_bigtime fails for incorrect attributes.
    """

    xfs_info = XFSInfo(
        mountpoint='/MOUNTPOINT',
        meta_data={'bigtime': bigtime} if bigtime else {},
        data={},
        naming={},
        log={},
        realtime={},
    )

    assert not checkoldxfs._has_valid_bigtime(xfs_info)


def test_has_valid_crc_passes():
    """
    Test _has_valid_crc passes for correct attributes.
    """

    xfs_info = XFSInfo(
        mountpoint='/MOUNTPOINT',
        meta_data={'crc': '1'},
        data={},
        naming={},
        log={},
        realtime={},
    )

    assert checkoldxfs._has_valid_crc(xfs_info)


@pytest.mark.parametrize("crc", ['0', '', '<UNKNOWN>', None])
def test_has_valid_crc_fail(crc):
    """
    Test _has_valid_crc fails for incorrect attributes.
    """

    xfs_info = XFSInfo(
        mountpoint='/MOUNTPOINT',
        meta_data={'crc': crc} if crc else {},
        data={},
        naming={},
        log={},
        realtime={},
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
                    meta_data={'crc': '1', 'bigtime': '1'},
                    data={},
                    naming={},
                    log={},
                    realtime={},
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
                    meta_data={
                        'crc': '1' if valid_crc else '0',
                        'bigtime': '1' if valid_bigtime else '0',
                    },
                    data={},
                    naming={},
                    log={},
                    realtime={},
                ),
            ]
        )
    ]))

    checkoldxfs.process()

    produced_title = reporting.create_report.report_fields.get('title')
    produced_summary = reporting.create_report.report_fields.get('summary')

    assert reporting.create_report.called == 1
    assert 'inhibited due to incompatible XFS filesystems' in produced_title
    assert 'Some XFS filesystems' in produced_summary
    assert reporting.create_report.report_fields['severity'] == reporting.Severity.HIGH
    assert is_inhibitor(reporting.create_report.report_fields)
