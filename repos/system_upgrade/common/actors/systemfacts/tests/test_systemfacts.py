from leapp.libraries.actor.systemfacts import anyendswith, anyhasprefix, aslist
from leapp.snactor.fixture import current_actor_libraries


def test_anyendswith(current_actor_libraries):
    value = 'this_is_a_test'

    assert anyendswith(value, ['a_test'])
    assert anyendswith(value, ['a_test', 'bgerwh', 'g52h4q'])
    assert anyendswith(value, ['est'])
    assert not anyendswith(value, ['asafsaf', 'gbfdshh', '123f', 'gdsgsnb'])
    assert not anyendswith(value, [])


def test_anyhasprefix(current_actor_libraries):
    value = 'this_is_a_test'

    assert anyhasprefix(value, ['this'])
    assert anyhasprefix(value, ['this', 'ddsvssd', 'bsdhn', '125fff'])
    assert anyhasprefix(value, ['this_is'])
    assert not anyhasprefix(value, ['ccbbb', 'xasbnn', 'xavavav', 'bbnkk1'])
    assert not anyhasprefix(value, [])


def test_aslist(current_actor_libraries):

    @aslist
    def local():
        yield True
        yield False
        yield True

    r = local()

    assert isinstance(r, list) and r[0] and r[2] and not r[1]
