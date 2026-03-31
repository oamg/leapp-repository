from unittest import mock

import pytest

from leapp.libraries.actor import regenerategrubcfg
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import DefaultGrub, DefaultGrubInfo

GRUB2_MKCONFIG_CMD = ['grub2-mkconfig', '-o', '/boot/grub2/grub.cfg']

BLS_ENABLED = DefaultGrubInfo(
    default_grub_info=[DefaultGrub(name='GRUB_ENABLE_BLSCFG', value='true')]
)
BLS_DISABLED = DefaultGrubInfo(
    default_grub_info=[DefaultGrub(name='GRUB_ENABLE_BLSCFG', value='false')]
)


@pytest.fixture
def mocked_run():
    with mock.patch.object(regenerategrubcfg, 'run') as m:
        yield m


@pytest.fixture(autouse=True)
def mocked_logger():
    with mock.patch.object(api, 'current_logger', logger_mocked()):
        yield api.current_logger


@pytest.fixture
def mock_actor(monkeypatch):

    def make_mock(msgs, arch=architecture.ARCH_X86_64, is_conversion=False):
        instance = CurrentActorMocked(
            msgs=msgs,
            arch=arch,
            src_ver="8.10",
            dst_ver="9.6",
        )
        monkeypatch.setattr(api, 'current_actor', instance)
        # let's use this to cover all conversion paths
        monkeypatch.setattr(regenerategrubcfg, 'is_conversion', lambda: is_conversion)
        return instance

    return make_mock


def test_conversion_bls_enabled_regenerates(mock_actor, mocked_run):
    """Conversion with BLS enabled -> regenerate."""
    mock_actor([BLS_ENABLED], is_conversion=True)
    regenerategrubcfg.process()
    mocked_run.assert_called_once_with(GRUB2_MKCONFIG_CMD)


def test_conversion_bls_disabled_skips(mock_actor, mocked_run):
    """Conversion with BLS not enabled -> skip."""
    mock_actor([BLS_DISABLED], is_conversion=True)
    regenerategrubcfg.process()
    mocked_run.assert_not_called()


def test_non_conversion_skips(mock_actor, mocked_run):
    """Non-conversion upgrade -> skip."""
    mock_actor([BLS_ENABLED])
    regenerategrubcfg.process()
    mocked_run.assert_not_called()


def test_s390x_skips(mock_actor, mocked_run):
    """s390x -> skip (uses ZIPL)."""
    mock_actor([BLS_ENABLED], arch=architecture.ARCH_S390X)
    regenerategrubcfg.process()
    mocked_run.assert_not_called()


def test_no_default_grub_info_skips(mock_actor, mocked_run, mocked_logger):
    """No DefaultGrubInfo -> skip."""
    mock_actor([], is_conversion=True)
    regenerategrubcfg.process()
    mocked_run.assert_not_called()
    assert any(
        "No DefaultGrubInfo message, skipping GRUB config regeneration." in msg
        for msg in mocked_logger.warnmsg
    )


def test_failure_nonfatal(mock_actor, mocked_run, mocked_logger):
    """grub2-mkconfig failure -> non-fatal, logs error."""
    mocked_run.side_effect = CalledProcessError(
        message='A Leapp Command Error occurred.',
        command=GRUB2_MKCONFIG_CMD,
        result={'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': 'fake', 'stderr': 'fake'}
    )
    mock_actor([BLS_ENABLED], is_conversion=True)

    regenerategrubcfg.process()

    mocked_run.assert_called_once_with(GRUB2_MKCONFIG_CMD)
    assert any('Failed to regenerate GRUB config' in msg for msg in mocked_logger.errmsg)
