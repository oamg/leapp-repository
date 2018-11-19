from leapp.actors import Actor
from leapp.tags import ExperimentalTag, IPUWorkflowTag, AttachPackageReposPhaseTag
from shutil import copyfile


class PatchDnf(Actor):
    name = 'patch_dnf'
    description = 'This actor applies a temporary workaround to make transactions to RHEL8 work.'
    consumes = ()
    produces = ()
    tags = (ExperimentalTag, IPUWorkflowTag, AttachPackageReposPhaseTag)

    def process(self):
        copyfile(self.get_file_path('base.py'), '/lib/python2.7/site-packages/dnf/base.py')
