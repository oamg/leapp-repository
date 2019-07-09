from leapp.libraries import stdlib
from leapp.libraries.stdlib import api
from leapp.models import InstalledTargetKernelVersion


def process():
    kernels = stdlib.run(["rpm", "-q", "kernel"], split=True)["stdout"]
    for kernel in kernels:
        version = kernel.split("-", 1)[1]
        if "el8" in version:
            api.produce(InstalledTargetKernelVersion(version=version))
            break
