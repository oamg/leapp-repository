from leapp.actors import Actor
from leapp.libraries.actor import library
from leapp.models import UsedTargetRepositories
from leapp.tags import FirstBootPhaseTag, IPUWorkflowTag


class EnableCRBrepo(Actor):
    """
    Enable CRB repository when used during the upgrade.
    """
    # TODO: replace this actor by more robust one which will enable repositories
    # based on msg; be careful about the solution as there is similar thing
    # for the upgrade process already - see the RepositoriesSetupTasks model

    name = 'enable_crb_repo'
    consumes = (UsedTargetRepositories,)
    produces = ()
    tags = (IPUWorkflowTag, FirstBootPhaseTag)

    def process(self):
        library.process()
