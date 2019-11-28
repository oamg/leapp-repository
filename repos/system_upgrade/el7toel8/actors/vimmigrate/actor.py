from leapp.actors import Actor
from leapp.libraries.actor import library
from leapp.libraries.common.rpms import has_package
from leapp.models import InstalledRedHatSignedRPM
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class VimMigrate(Actor):
    """
    Modify configuration files of Vim 8.0 and later to keep the same behavior
    as Vim 7.4 and earlier had.
    """

    name = 'vim_migrate'
    consumes = (InstalledRedHatSignedRPM,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        error_list = []

        for pkg, config_file in library.vim_configs.items():
            if not has_package(InstalledRedHatSignedRPM, pkg):
                continue
            try:
                library.update_config(config_file, library.append_string)
            except (OSError, IOError) as error:
                self.log.warning('Cannot modify the {} config file.'.format(config_file))
                error_list.append((config_file, error))
        if error_list:
            self.log.error('The files below have not been modified (error message included):' +
                           ''.join(['\n    - {}: {}'.format(err[0], err[1]) for err in error_list]))
            return
