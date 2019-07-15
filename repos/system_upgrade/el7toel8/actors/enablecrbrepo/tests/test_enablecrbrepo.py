from leapp.libraries.actor import library
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import UsedTargetRepositories, UsedTargetRepository


class run_mocked(object):
    def __init__(self, raise_err=False):
        self.called = 0
        self.args = []
        self.raise_err = raise_err

    def __call__(self, *args):
        self.called += 1
        self.args.append(args)
        if self.raise_err:
            raise CalledProcessError(
                message='A Leapp Command Error occured.',
                command=args,
                result={'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': 'fake', 'stderr': 'fake'}
            )


class logger_mocked(object):
    def __init__(self):
        self.errmsg = None

    def error(self, *args):
        self.errmsg = args

    def __call__(self):
        return self


def construct_UTRepo_consume(repoids):
    repos = [UsedTargetRepository(repoid=repoid) for repoid in repoids]
    return lambda *x: (x for x in (UsedTargetRepositories(repos=repos),))


def test_is_crb_used_false(monkeypatch):
    inputs = ([], ['some-name'], ['some-name', 'another-repo'])
    for i in inputs:
        monkeypatch.setattr(api, 'consume', construct_UTRepo_consume(i))
        assert not library._is_crb_used()


def test_is_crb_used_true(monkeypatch):
    inputs = ([library.CRB_REPOID], ['some-name', library.CRB_REPOID])
    for i in inputs:
        monkeypatch.setattr(api, 'consume', construct_UTRepo_consume(i))
        assert library._is_crb_used()


def test_process_setrepo(monkeypatch):
    monkeypatch.setattr(library, 'run', run_mocked())
    monkeypatch.setattr(library, '_is_crb_used', lambda: True)
    library.process()
    assert library.run.called
    assert 'subscription-manager' in library.run.args[0][0]
    assert library.CRB_REPOID in library.run.args[0][0]


def test_process_donothing(monkeypatch):
    monkeypatch.setattr(library, 'run', run_mocked())
    monkeypatch.setattr(library, '_is_crb_used', lambda: False)
    library.process()
    assert not library.run.called


def test_process_fail(monkeypatch):
    monkeypatch.setattr(library, 'run', run_mocked(raise_err=True))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(library, '_is_crb_used', lambda: True)
    library.process()
    assert library.run.called
    assert api.current_logger.errmsg
