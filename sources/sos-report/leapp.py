from sos.plugins import Plugin, RedHatPlugin


class Leapp(Plugin, RedHatPlugin):
    """
    This plugin is used to gather all information necessary for reporting
    problems in regards to the leapp application.
    """

    plugin_name = 'leapp'
    packages = ('leapp', 'leapp-repository')

    def setup(self):
        self.add_copy_spec([
            '/var/lib/leapp/leapp.db',
            '/tmp/download-debugdata',
            '/var/log/upgrade.log',
            '/tmp/leapp-report.txt'
        ])
