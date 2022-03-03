import pytest

from leapp.libraries.actor import yumconfigscanner

CMD_YUM_OUTPUT = '''Loaded plugins: langpacks, my plugin, subscription-manager, product-id
Usage: yum [options] COMMAND
'''
CMD_YUM_OUTPUT_MULTILINE_BREAK_ON_HYPHEN = '''Loaded plugins: langpacks, my plugin, subscription-
              : manager, product-id
Usage: yum [options] COMMAND
'''
CMD_YUM_OUTPUT_MULTILINE_BREAK_ON_WHITESPACE = '''Loaded plugins: langpacks, my plugin,
              : subscription-manager, product-id
Usage: yum [options] COMMAND
'''


def assert_plugins_identified_as_enabled(expected_plugins, identified_plugins):
    fail_description = 'Failed to parse a plugin from the yum output.'
    for expected_enabled_plugin in expected_plugins:
        assert expected_enabled_plugin in identified_plugins, fail_description


@pytest.mark.parametrize(
    ('source_major_version', 'yum_command'),
    [
        ('7', ['yum', '--setopt=debuglevel=2']),
        ('8', ['dnf', '-v']),
    ]
)
def test_scan_enabled_plugins(monkeypatch, source_major_version, yum_command):
    """Tests whether the enabled plugins are correctly retrieved from the yum output."""

    def run_mocked(cmd, **kwargs):
        if cmd == yum_command:
            return {
                'stdout': CMD_YUM_OUTPUT.split('\n'),
                'stderr': 'You need to give some command',
                'exit_code': 1
            }
        raise ValueError('Tried to run an unexpected command.')

    def get_source_major_version_mocked():
        return source_major_version

    # The library imports `run` all the way into its namespace (from ...stdlib import run),
    # we must overwrite it there then:
    monkeypatch.setattr(yumconfigscanner, 'run', run_mocked)
    monkeypatch.setattr(yumconfigscanner, 'get_source_major_version', get_source_major_version_mocked)

    enabled_plugins = yumconfigscanner.scan_enabled_yum_plugins()
    assert_plugins_identified_as_enabled(
        ['langpacks', 'my plugin', 'subscription-manager', 'product-id'],
        enabled_plugins
    )


@pytest.mark.parametrize(
    ('yum_output',),
    [
        (CMD_YUM_OUTPUT,),
        (CMD_YUM_OUTPUT_MULTILINE_BREAK_ON_HYPHEN,),
        (CMD_YUM_OUTPUT_MULTILINE_BREAK_ON_WHITESPACE,)
    ])
def test_yum_loaded_plugins_multiline_output(yum_output, monkeypatch):
    """Tests whether the library correctly handles yum plugins getting reported on multiple lines."""
    def run_mocked(cmd, **kwargs):
        return {
            'stdout': yum_output.split('\n'),
            'stderr': 'You need to give some command',
            'exit_code': 1
        }

    monkeypatch.setattr(yumconfigscanner, 'run', run_mocked)
    monkeypatch.setattr(yumconfigscanner, 'get_source_major_version', lambda: '7')

    enabled_plugins = yumconfigscanner.scan_enabled_yum_plugins()

    assert len(enabled_plugins) == 4, 'Identified more yum plugins than available in the mocked yum output.'
    assert_plugins_identified_as_enabled(
        ['langpacks', 'my plugin', 'subscription-manager', 'product-id'],
        enabled_plugins
    )
