import pytest

from leapp.libraries.actor import insightsautoregister
from leapp.libraries.common import rhsm
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError


@pytest.mark.parametrize(
    ('skip_rhsm', 'no_register', 'should_register'),
    [
        (False, False, True),
        (False, True, False),
        (True, False, False),
        (True, True, False),
    ]
)
def test_should_register(monkeypatch, skip_rhsm, no_register, should_register):
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: skip_rhsm)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        envars={'LEAPP_NO_INSIGHTS_REGISTER': '1' if no_register else '0'}
        ))

    called = []

    def _insights_register_mocked():
        called.append(True)

    monkeypatch.setattr(
        insightsautoregister,
        '_insights_register',
        _insights_register_mocked
    )

    insightsautoregister.process()

    assert len(called) == should_register


def test_insights_register_success_logged(monkeypatch):

    def run_mocked(cmd, **kwargs):
        return {
            'stdout': 'Successfully registered into Insights',
            'stderr': '',
            'exit_code': 0
        }

    monkeypatch.setattr(insightsautoregister, 'run', run_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    insightsautoregister._insights_register()

    assert api.current_logger.infomsg
    assert not api.current_logger.errmsg


def test_insights_register_failure_logged(monkeypatch):

    def run_mocked(cmd, **kwargs):
        raise CalledProcessError(
            message='A Leapp Command Error occurred.',
            command=cmd,
            result={'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': 'fake', 'stderr': 'fake'}
        )

    monkeypatch.setattr(insightsautoregister, 'run', run_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    insightsautoregister._insights_register()

    assert not api.current_logger.infomsg
    assert api.current_logger.errmsg
