import os

from leapp.libraries.actor import systemfacts
from leapp.models import DefaultGrub


class RunMocked(object):
    def __init__(self, cmd_result):
        self.called = 0
        self.cmd_result = cmd_result
        self.split = False
        self.cmd = None

    def __call__(self, cmd, split=False):
        self.cmd = cmd
        self.split = split
        self.called += 1
        return self.cmd_result


def test_default_grub_info_valid(monkeypatch):
    mocked_run = RunMocked({
        'stdout': [
            'line="whatever else here"',
            'newline="whatever"',
            '# comment here',
            'why_not=value',
            ' # whitespaces around comment ',
            ' ',
            ' last=last really'
        ],
    })
    expected_result = [
        DefaultGrub(name='line', value='"whatever else here"'),
        DefaultGrub(name='newline', value='"whatever"'),
        DefaultGrub(name='why_not', value='value'),
        DefaultGrub(name='last', value='last really'),
    ]
    monkeypatch.setattr(systemfacts, 'run', mocked_run)
    monkeypatch.setattr(os.path, 'isfile', lambda dummy: True)
    for msg in systemfacts._default_grub_info():
        expected_msg = expected_result.pop(0)
        assert msg.name == expected_msg.name
        assert msg.value == expected_msg.value
    assert mocked_run.called
    assert not expected_result
