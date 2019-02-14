import csv

from leapp.actors import Actor
from leapp.models import RepositoriesMap, RepositoryMap
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag


class RepositoriesMapping(Actor):
    """
    Produces message containing repository mapping based on provided file.
    """

    name = 'repository_mapping'
    consumes = ()
    produces = (RepositoriesMap,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    
    def process(self):
        repos_maps = RepositoriesMap()

        with open(self.get_file_path('repomap.csv')) as f:
            data = csv.reader(f)
            next(data) # skip header
            for row in data:
                if len(row) != 6:
                    continue
                
                from_id, to_id, from_minor_version, to_minor_version, arch, repo_type = row

                repos_maps.repositories.append(RepositoryMap(from_id=from_id,
                                                             to_id=to_id,
                                                             from_minor_version=from_minor_version,
                                                             to_minor_version=to_minor_version,
                                                             arch=arch,
                                                             repo_type=repo_type))
        self.produce(repos_maps)
