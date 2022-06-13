from leapp.libraries.stdlib import api
from leapp.models import RequiredTargetUserspacePackages  # deprecated
from leapp.models import (
    CustomTargetRepositoryFile,
    RHSMInfo,
    RHUIInfo,
    StorageInfo,
    TargetUserSpacePreupgradeTasks,
    XFSPresence
)
from leapp.utils.deprecation import suppress_deprecation


def _consume_one(model, default=None):
    return next(api.consume(model), default)


def _consume_list(model):
    return list(api.consume(model))


class _InputData(object):
    def __init__(self):
        self.packages = {'dnf', 'dnf-command(config-manager)'}
        self.files = []
        self._cftuples = set()
        self.rhsm_info = _consume_one(RHSMInfo)
        self.rhui_info = _consume_one(RHUIInfo)
        self.custom_repofiles = _consume_list(CustomTargetRepositoryFile)
        self.xfs_info = _consume_one(XFSPresence, XFSPresence())
        self.storage_info = _consume_one(StorageInfo, None)
        self._consume_data()

    def _update_files(self, message):
        # add just uniq CopyFile objects to omit duplicate copying of files
        for cfile in message.copy_files:
            cftuple = (cfile.src, cfile.dst)
            if cftuple not in self._cftuples:
                self._cftuples.add(cftuple)
                self.files.append(cfile)

    def _package_update(self, model, field_name, next=None):
        for message in api.consume(model):
            self.packages.update(getattr(message, field_name))
            if next:
                next(message)

    @suppress_deprecation(RequiredTargetUserspacePackages)
    def _consume_data(self):
        """
        Wrapper function to consume majority input data.

        It doesn't consume TargetRepositories, which are consumed in the
        own function.
        """
        self._package_update(TargetUserSpacePreupgradeTasks, 'install_rpms', self._update_files)
        self._package_update(RequiredTargetUserspacePackages, 'packages')

        if not self.rhsm_info and not rhsm.skip_rhsm():
            api.current_logger().warning('Could not receive RHSM information - Is this system registered?')
            raise StopActorExecution()
        if rhsm.skip_rhsm() and self.rhsm_info:
            # this should not happen. if so, raise an error as something in
            # other actors is wrong really
            raise StopActorExecutionError("RHSM is not handled but the RHSMInfo message has been produced.")

        if not self.storage_info:
            raise StopActorExecutionError('No storage info available cannot proceed.')
