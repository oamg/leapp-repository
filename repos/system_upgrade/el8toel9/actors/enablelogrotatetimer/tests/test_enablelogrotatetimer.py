from leapp.libraries.actor import enablelogrotatetimer
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError


def test_success(monkeypatch):

    def mock_enable_unit(unit):
        assert unit == 'logrotate.timer'

    monkeypatch.setattr(enablelogrotatetimer, "enable_unit", mock_enable_unit)
    enablelogrotatetimer.process()


def test_failed_to_enable(monkeypatch):

    def mock_enable_unit(unit):
        assert unit == 'logrotate.timer'
        raise CalledProcessError(
            "Failed to enable logrotate.titmer",
            ["systemctl", "enable", "logrotate.timer"],
            {
                "exit_code": 1,
                "stderr": "err",
            },
        )

    monkeypatch.setattr(enablelogrotatetimer, "enable_unit", mock_enable_unit)
    monkeypatch.setattr(api, "current_logger", logger_mocked())
    enablelogrotatetimer.process()
    assert "Failed to enable logrotate.timer" in api.current_logger.errmsg[0]
