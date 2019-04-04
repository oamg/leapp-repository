from leapp.libraries.actor import library


class run_mocked(object):
    def __init__(self):
        self.called = 0

    def __call__(self, args, split=True):
        self.called += 1
        self.args = args
        return True


def test_prepare_yum_config(monkeypatch):
    monkeypatch.setattr('library.run', run_mocked())
    library.prepare_yum_config()
    assert library.run.called == 1
    assert library.run.args == ['handleyumconfig']
