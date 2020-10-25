from leapp.libraries.actor import quaggadaemons
from leapp.models import QuaggaToFrrFacts

# daemons for mocked _check_service function
TEST_DAEMONS = ['bgpd', 'ospfd', 'zebra']


def mock_check_service(name, state):
    if name in TEST_DAEMONS:
        return True

    return False


def test_process_daemons():
    quaggadaemons._check_service = mock_check_service

    facts = quaggadaemons.process_daemons()
    assert isinstance(facts, QuaggaToFrrFacts)
    assert facts.active_daemons == TEST_DAEMONS
    assert facts.enabled_daemons == TEST_DAEMONS
