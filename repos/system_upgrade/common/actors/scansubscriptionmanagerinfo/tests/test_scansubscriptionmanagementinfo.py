import pytest

from leapp.libraries.actor import scanrhsm
from leapp.libraries.common import rhsm
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import RepositoryData, RepositoryFile, RHSMInfo


def mocked_get_rhsm_info(context):
    assert context, 'The actor did not provide library with valid context.'
    info = RHSMInfo()
    info.attached_skus = ['SKU1', 'SKU2']
    info.available_repos = ['Repo1', 'Repo2']
    info.enabled_repos = ['Repo2']
    info.release = '7.9'
    info.existing_product_certificates = ['Cert1', 'Cert2', 'Cert3']
    info.sca_detected = True
    return info


def test_scansubscriptionmanagementinfo(monkeypatch):
    actor_producs = produce_mocked()

    monkeypatch.setattr(rhsm, 'scan_rhsm_info', mocked_get_rhsm_info)
    monkeypatch.setattr(api, 'produce', actor_producs)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    scanrhsm.scan()

    assert actor_producs.model_instances, 'The actor did not produce any message.'
    assert len(actor_producs.model_instances) == 1, 'The actor produced more messages than expected.'

    message = actor_producs.model_instances[0]

    # The actor does not do much more than calling the `rhsm` library (which has its own tests),
    # just check that the message has not changed
    assert message.attached_skus == ['SKU1', 'SKU2']
    assert message.available_repos == ['Repo1', 'Repo2']
    assert message.enabled_repos == ['Repo2']
    assert message.release == '7.9'
    assert message.existing_product_certificates == ['Cert1', 'Cert2', 'Cert3']
    assert message.sca_detected
