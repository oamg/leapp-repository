import os

from leapp.actors import Actor
from leapp.tags import IPUWorkflowTag,  RPMUpgradePhaseTag


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
        leapp_home = "/root/tmp_leapp_py3"
        py3_leapp = os.path.join(leapp_home, "leapp3")
        os.mkdir(leapp_home)
        os.symlink(
                "/usr/lib/python2.7/site-packages/leapp",
                os.path.join(leapp_home, "leapp"))
        with open(py3_leapp, "w") as f:
            f_content = [
                "#!/usr/bin/python3",
                "import sys",
                "sys.path.append('{}')".format(leapp_home),
                "",
                "import leapp.cli",
                "sys.exit(leapp.cli.main())",
                ]
            f.write("{}\n\n".format("\n".join(f_content)))
        os.chmod(py3_leapp, 0o770)
