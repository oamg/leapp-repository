from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import version
from leapp.models import DracutModule, FIPSInfo, Report, UpgradeInitramfsTasks
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckFips(Actor):
    """
    Inhibit upgrade if FIPS is detected as enabled.
    """

    name = 'check_fips'
    consumes = (FIPSInfo,)
    produces = (Report, UpgradeInitramfsTasks)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        fips_info = next(self.consume(FIPSInfo), None)

        if not fips_info:
            raise StopActorExecutionError(
                "Cannot check FIPS state due to not receiving necessary FIPSInfo message",
                details={
                    "Problem": "Did not receive a message with information about FIPS usage"
                },
            )

        if version.get_target_major_version() == '9':
            # FIXME(mhecko): We include these files manually as they are not
            # included automatically when the fips module is used due to a bug
            # in dracut. This code should be removed, once the dracut bug is
            # resolved. See https://bugzilla.redhat.com/show_bug.cgi?id=2176560
            if fips_info.is_enabled:
                fips_required_initramfs_files = [
                    '/etc/crypto-policies/back-ends/opensslcnf.config',
                    '/etc/pki/tls/openssl.cnf',
                    '/usr/lib64/ossl-modules/fips.so',
                ]
                self.produce(
                    UpgradeInitramfsTasks(
                        include_files=fips_required_initramfs_files,
                        include_dracut_modules=[DracutModule(name='fips')],
                    )
                )
        elif version.get_target_major_version() == '10':
            # TODO(mmatuska): What to do with FIPS on 9to10? OAMG-11431
            pass
