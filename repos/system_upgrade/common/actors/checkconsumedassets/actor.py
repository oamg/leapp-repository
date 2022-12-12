from leapp.actors import Actor
from leapp.libraries.actor import check_consumed_assets
from leapp.models import ConsumedDataAsset, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckConsumedAssets(Actor):
    """
    Check whether Leapp is using correct data assets.
    """

    name = 'check_consumed_assets'
    consumes = (ConsumedDataAsset,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        check_consumed_assets.inhibit_if_assets_with_incorrect_version()
