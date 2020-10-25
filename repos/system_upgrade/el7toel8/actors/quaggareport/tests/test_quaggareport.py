import pytest

from leapp.models import QuaggaToFrrFacts
from leapp.snactor.fixture import ActorContext


# TODO We can't use caplog here as logs from other processes is
#  hard to capture and caplog not see it.
@pytest.mark.parametrize(
    ("quagga_facts", "active_daemons", "has_report", "msg_in_log"),
    [
        (True, ["babeld"], True, None),
        (True, ["something_else"], False, "babeld not used, moving on"),
        (False, [], False, None),
    ],
)
def test_quaggareport(
    monkeypatch,
    current_actor_context,
    quagga_facts,
    active_daemons,
    has_report,
    msg_in_log,
):
    """Test quaggareport.

    :type current_actor_context:ActorContext
    """
    if quagga_facts:
        current_actor_context.feed(
            QuaggaToFrrFacts(
                active_daemons=active_daemons,
                enabled_daemons=["bgpd", "ospfd", "zebra"],
            )
        )
    current_actor_context.run()
    if has_report:
        assert current_actor_context.messages()[0]["type"] == "Report"
    if msg_in_log:
        assert not current_actor_context.messages()
