from leapp.actors import Actor
from leapp.libraries.actor import deviceanddriverdeprecationdataload
from leapp.models import ConsumedDataAsset, DeviceDriverDeprecationData
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class LoadDeviceDriverDeprecationData(Actor):
    """
    Loads deprecation data for drivers and devices (PCI & CPU)

    The data will either be loaded from the local /etc/leapp/files location or
    fetched from the Red Hat remote service providing this data.
    """

    name = 'load_device_driver_deprecation_data'
    consumes = ()
    produces = (DeviceDriverDeprecationData, ConsumedDataAsset)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self, *args, **kwargs):
        deviceanddriverdeprecationdataload.process()
