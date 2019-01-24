from leapp.actors import Actor
from leapp.models import RHELTargetRepository, TargetRepositories
from leapp.models import CustomTargetRepository
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag


class SetupTargetRepos(Actor):
    name = 'setuptargetrepos'
    description = ('Produces list of repositories that should be used and'
                   ' available for upgrade to the target system, based on'
                   ' the current set of RHEL repositories. Additionaly'
                   ' process request to use custom repositories during the'
                   ' upgrade transaction')
    consumes = (CustomTargetRepository,)
    produces = (TargetRepositories,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        # FIXME: currently we will use always only two repositories, unaffected
        # + by the current list of enabled repositories.
        # TODO: Should use CSV file as the source of information for upgrade
        # + from source system to the target system
        # TODO: Think about Beta and Alpha repositories. How will we tell we
        # + want to go to GA, Alpha, Beta, ... repos?

        custom_repos = []
        for repo in self.consume(CustomTargetRepository):
            custom_repos.append(repo)

        rhel_repos = []
        for repo_uid in ("rhel-8-for-x86_64-baseos-htb-rpms", "rhel-8-for-x86_64-appstream-htb-rpms"):
            rhel_repos.append(RHELTargetRepository(uid=repo_uid))

        self.produce(TargetRepositories(
            rhel_repos=rhel_repos,
            custom_repos=custom_repos,
        ))

        # TODO: Some informational messages would be added for the report and
        # + logs, so we and user will know exactly what is going on.

        return
