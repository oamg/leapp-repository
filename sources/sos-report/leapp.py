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
            '/var/log/leapp/dnf-debugdata/',
            '/var/log/leapp/leapp-upgrade.log',
            '/var/log/leapp/leapp-report.txt',
            '/var/log/leapp/dnf-plugin-data.txt'
        ])

        # capture DB without sizelimit
        self.add_copy_spec('/var/lib/leapp/leapp.db', sizelimit=0)
