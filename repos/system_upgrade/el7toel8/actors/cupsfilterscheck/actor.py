from leapp.actors import Actor
from leapp.libraries.common.reporting import report_generic
from leapp.models import Report, InstalledRedHatSignedRPM, CupsFiltersModel
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag

from subprocess import Popen, PIPE

class CupsfiltersCheck(Actor):
    """
    cupsfilters_check actor

    Checks if cups-filters package is installed and if cups-browsed.conf was
    modified by user, which prevents automatic replacement by package installer.
    """

    name = 'cupsfilters_check'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report, CupsFiltersModel)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
      installed_cupsfilters = False
      migrateable = False

      for rpm_pkgs in self.consume(InstalledRedHatSignedRPM):
        for pkg in rpm_pkgs.items:
          if pkg.name == "cups-filters":
            installed_cupsfilters = True

      if installed_cupsfilters is False:
        report_generic(
                        title='cups-filters will not be migrated',
                        summary='cups-filters is not installed',
                        severity='low'
                      )
        migrateable = False
      else:
        # Always migrateable when installed, because post install script
        # modifies the configuration file
        migrateable = True

      if migrateable is True:
        report_generic(
                        title='Package cups-filters will be migrated',
                        summary='The package is installed and configuration file is modified by user.',
                        severity='low'
                      )

      self.produce(CupsFiltersModel(migrateable=migrateable))
