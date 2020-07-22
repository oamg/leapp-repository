from leapp.actors import Actor
from leapp.libraries.actor.workaround import apply_python3_workaround
from leapp.tags import IPUWorkflowTag, RPMUpgradePhaseTag


class PreparePythonWorkround(Actor):
    """
    Prepare environment to be able to run leapp with Python3 in initrd.

    These are the current necessary steps to be able to run Leapp with Python3.
    Basically, we create directory (now /root/tmp_leapp_py3/). We will put
    symlinks inside which will point to leapp python packages. Additionally,
    we create new script that will import expected modules and run leapp again.
    """

    name = 'prepare_python_workround'
    consumes = ()
    produces = ()
    tags = (IPUWorkflowTag, RPMUpgradePhaseTag)

    def process(self):
        apply_python3_workaround()
