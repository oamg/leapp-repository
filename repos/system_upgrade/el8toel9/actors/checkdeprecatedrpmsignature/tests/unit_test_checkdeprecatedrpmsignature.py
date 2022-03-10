import pytest

# from leapp import reporting
from leapp.libraries.actor import checkdeprecatedrpmsignature

# from leapp.libraries.common.testutils import CurrentActorMocked
# from leapp.libraries.stdlib import api


@pytest.mark.parametrize('curr_state,expected_res', (
    ('LEGACY', True),
    ('DEFAULT:SHA1', True),
    ('MYPOL:SHA1', False),
    ('DEFAULT', False),
    ('NOLEGACY', False),
    ('SOMETHING:SHA-512', False),
    ('SOMETHING:-SHA1', False),
    ('DEFAULT:-SHA1', False),
))
def test_sha_allowed(curr_state, expected_res):
    assert expected_res == checkdeprecatedrpmsignature._is_sha1_allowed(curr_state)

# TODO: def test_get_rpms_sha1_sig()
# TODO: test_inhibitor_create
