import pytest

from leapp import reporting
from leapp.libraries.actor import check_consumed_assets as check_consumed_assets_lib
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import ConsumedDataAsset
from leapp.utils.report import is_inhibitor


@pytest.mark.parametrize(('asset_data_streams', 'inhibit_reason'),
                         ((['10.0'], None),
                          (['9.3', '10.1', '11.0'], None),
                          (['11.1'], 'incompatible'),
                          (['3.1', '4.0'], 'incompatible'),
                          (['11.1', '12.0'], 'incompatible'),
                          ([], 'malformed'),
                          (['malformed'], 'malformed')))
def test_asset_version_correctness_assessment(monkeypatch, asset_data_streams, inhibit_reason):

    monkeypatch.setattr(check_consumed_assets_lib, 'get_consumed_data_stream_id', lambda: '10.0')
    used_asset = ConsumedDataAsset(filename='asset.json',
                                   fulltext_name='',
                                   docs_url='',
                                   docs_title='',
                                   provided_data_streams=asset_data_streams)

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[used_asset]))
    create_report_mock = create_report_mocked()
    monkeypatch.setattr(reporting, 'create_report', create_report_mock)

    check_consumed_assets_lib.inhibit_if_assets_with_incorrect_version()

    expected_report_count = 1 if inhibit_reason else 0
    assert create_report_mock.called == expected_report_count
    if inhibit_reason:
        report = create_report_mock.reports[0]
        assert is_inhibitor(report)
        assert inhibit_reason in report['title'].lower()


def test_make_report_entries_with_unique_urls():
    # Check that multiple titles produce one report
    docs_url_to_title_map = {'/path/to/asset1': ['asset1_title1', 'asset1_title2'],
                             '/path/to/asset2': ['asset2_title']}
    report_urls = check_consumed_assets_lib.make_report_entries_with_unique_urls(docs_url_to_title_map)
    assert set([ru.value['url'] for ru in report_urls]) == {'/path/to/asset1', '/path/to/asset2'}
