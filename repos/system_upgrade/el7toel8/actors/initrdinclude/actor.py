
from leapp.actors import Actor
from leapp.models import InitrdIncludes
from leapp.tags import IPUWorkflowTag, FinalizationPhaseTag
from leapp.libraries.stdlib import run, CalledProcessError
from leapp.exceptions import StopActorExecutionError


class InitrdInclude(Actor):
    """
    Regenerate RHEL-8 initrd and include files produced by other actors
    """

    name = 'initrdinclude'
    consumes = (InitrdIncludes, )
    produces = ()
    tags = (FinalizationPhaseTag, IPUWorkflowTag)

    def get_rhel8_kernel_version(self):
        kernels = run(["rpm", "-q", "kernel"], split=True)["stdout"]
        for kernel in kernels:
            version = kernel.split("-", 1)[1]
            if "el8" in version:
                return version
        raise StopActorExecutionError(
            "Cannot get version of the installed RHEL-8 kernel",
            details={"details": "\n".join(kernels)})

    def process(self):
        files = []

        for i in self.consume(InitrdIncludes):
            files += i.files

        if not files:
            self.log.debug("No additional files required to add into the initrd.")
            return

        # TODO(pstodulk): consume message that provides info about currently
        # # installed rpms; - it doesn't exist yet
        try:
            kernel_version = self.get_rhel8_kernel_version()
            self.log.debug("The detected RHEL 8 kernel: {}".format(kernel_version))
        except CalledProcessError as e:
            # just hypothetic check, it should not die
            # NOTE(pstodulk): raise an exception and stop leapp execution now?
            raise StopActorExecutionError(
                "Cannot get info about the installed kernel.",
                details={"details": str(e)})
        try:
            cmd = ["dracut", "--install", " ".join(files), "-f", "--kver", kernel_version]
            run(cmd)
        except CalledProcessError as e:
            # NOTE(pstodulk) same note as above
            raise StopActorExecutionError(
                "Cannot regenerate dracut image.",
                details={"details": str(e)})
