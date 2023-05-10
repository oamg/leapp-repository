from leapp.actors import Actor
from leapp.libraries.actor import check_fips as check_fips_lib
from leapp.models import FIPSInfo
from leapp.tags import IPUWorkflowTag, LateTestsPhaseTag


class CheckFIPSCorrectlyEnabled(Actor):
    """
    Sanity check to stop the IPU if the system did not boot into the upgrade initramfs with FIPS settings preserved.

    The performed check should be unlikely to fail, as it would mean that the upgrade boot entry was created without
    fips=1 on the kernel cmdline.
    """

    name = 'check_fips_correctly_enabled'
    consumes = (FIPSInfo,)
    produces = ()
    tags = (LateTestsPhaseTag, IPUWorkflowTag)

    def process(self):
        check_fips_lib.check_fips_state_perserved()
