from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import InitrdIncludes, InstalledTargetKernelVersion


def process():
    files = [f for i in api.consume(InitrdIncludes) for f in i.files]
    if not files:
        api.current_logger().debug("No additional files required to add into the initrd.")
        return

    target_kernel = next(api.consume(InstalledTargetKernelVersion), None)
    if not target_kernel:
        raise StopActorExecutionError(
            "Cannot get version of the installed RHEL-8 kernel",
            details={'Problem': 'Did not receive a message with installed RHEL-8 kernel version'
                                ' (InstalledTargetKernelVersion)'})

    try:
        # multiple files need to be quoted, see --install in dracut(8)
        cmd = ["dracut", "--install", '"' + " ".join(files) + '"', "-f", "--kver", target_kernel.version]
        run(cmd)
    except CalledProcessError as e:
        # just hypothetic check, it should not die
        raise StopActorExecutionError("Cannot regenerate dracut image.", details={"details": str(e)})
