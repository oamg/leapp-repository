import re
from collections import defaultdict, namedtuple

from leapp import reporting
from leapp.libraries.common.config import get_consumed_data_stream_id
from leapp.libraries.common.fetch import ASSET_PROVIDED_DATA_STREAMS_FIELD
from leapp.libraries.stdlib import api
from leapp.models import ConsumedDataAsset


def compose_summary_for_incompatible_assets(assets, incompatibility_reason):
    if not assets:
        return []

    summary_lines = ['The following assets are {reason}'.format(reason=incompatibility_reason)]
    for asset in assets:
        if asset.provided_data_streams is None:  # Assets with missing streams are placed only in .outdated bucket
            details = (' - The asset {what_asset} is missing information about provided data streams '
                       'in its metadata header')
            details = details.format(what_asset=asset.filename)
        else:
            article, multiple_suffix = ('the ', '') if len(asset.provided_data_streams) == 1 else ('', 's')
            details = ' - The asset {what_asset} provides {article}data stream{mult_suffix} {provided_streams}'
            details = details.format(what_asset=asset.filename,
                                     provided_streams=', '.join(asset.provided_data_streams),
                                     article=article, mult_suffix=multiple_suffix)
        summary_lines.append(details)
    return summary_lines


def make_report_entries_with_unique_urls(docs_url_to_title_map):
    report_urls = []
    # Add every unique asset URL into the report
    urls_with_multiple_titles = []
    for url, titles in docs_url_to_title_map.items():
        if len(titles) > 1:
            urls_with_multiple_titles.append(url)

        report_entry = reporting.ExternalLink(title=titles[0], url=url)
        report_urls.append(report_entry)

    if urls_with_multiple_titles:
        msg = 'Docs URLs {urls} are used with inconsistent URL titles, picking one.'
        api.current_logger().warning(msg.format(urls=', '.join(urls_with_multiple_titles)))

    return report_urls


def report_incompatible_assets(assets):
    if not any((assets.outdated, assets.too_new, assets.unknown)):
        return

    title = 'Incompatible Leapp data assets are present'

    docs_url_to_title_map = defaultdict(list)
    required_data_stream = get_consumed_data_stream_id()
    summary_prelude = ('The currently installed Leapp consumes data stream {consumed_data_stream}, but the '
                       'following assets provide different streams:')
    summary_lines = [summary_prelude.format(consumed_data_stream=required_data_stream)]

    assets_with_shared_summary_entry = [
        ('outdated', assets.outdated),
        ('intended for a newer leapp', assets.too_new),
        ('has an incorrect version', assets.unknown)
    ]

    doc_url_to_title = defaultdict(list)  # To make sure we do not spam the user with the same URLs
    for reason, incompatible_assets in assets_with_shared_summary_entry:
        summary_lines += compose_summary_for_incompatible_assets(incompatible_assets, reason)

        for asset in incompatible_assets:
            doc_url_to_title[asset.docs_url].append(asset.docs_title)

    report_parts = [
        reporting.Title(title),
        reporting.Summary('\n'.join(summary_lines)),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR, reporting.Groups.REPOSITORY]),
    ]

    report_parts += make_report_entries_with_unique_urls(docs_url_to_title_map)
    reporting.create_report(report_parts)


def report_malformed_assets(malformed_assets):
    if not malformed_assets:
        return

    title = 'Detected malformed Leapp data assets'
    summary_lines = ['The following assets are malformed:']

    docs_url_to_title_map = defaultdict(list)
    for asset in malformed_assets:
        if not asset.provided_data_streams:
            details = (' - The asset file {filename} contains no values in its "{provided_data_streams_field}" '
                       'field, or the field does not contain a list')
            details = details.format(filename=asset.filename,
                                     provided_data_streams_field=ASSET_PROVIDED_DATA_STREAMS_FIELD)
        else:
            # The asset is malformed because we failed to convert its major versions to ints
            details = ' - The asset file {filename} contains invalid value in its "{data_streams_field}"'
            details = details.format(filename=asset.filename, data_streams_field=ASSET_PROVIDED_DATA_STREAMS_FIELD)
        summary_lines.append(details)
        docs_url_to_title_map[asset.docs_url].append(asset.docs_title)

    report_parts = [
        reporting.Title(title),
        reporting.Summary('\n'.join(summary_lines)),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR, reporting.Groups.REPOSITORY]),
    ]

    report_parts += make_report_entries_with_unique_urls(docs_url_to_title_map)
    reporting.create_report(report_parts)


def inhibit_if_assets_with_incorrect_version():
    required_data_stream = get_consumed_data_stream_id()
    required_data_stream_major = int(required_data_stream.split('.', 1)[0])

    # The assets are collected according to why are they considered incompatible, so that a single report is created
    # for every class
    IncompatibleAssetsByType = namedtuple('IncompatibleAssets', ('outdated', 'too_new', 'malformed', 'unknown'))
    incompatible_assets = IncompatibleAssetsByType(outdated=[], too_new=[], malformed=[], unknown=[])

    datastream_version_re = re.compile(r'\d+\.\d+$')

    for consumed_asset in api.consume(ConsumedDataAsset):
        if consumed_asset.provided_data_streams is None:  # There is no provided_data_streams field
            # Most likely an old file that predates the introduction of versioning to data assets
            incompatible_assets.outdated.append(consumed_asset)
            continue

        # Ignore minor stream numbers and search only for a stream matching the same major number
        if all((datastream_version_re.match(stream) for stream in consumed_asset.provided_data_streams)):
            provided_major_data_streams = sorted(
                int(stream.split('.', 1)[0]) for stream in consumed_asset.provided_data_streams
            )
        else:
            incompatible_assets.malformed.append(consumed_asset)
            continue

        if required_data_stream_major in provided_major_data_streams:
            continue

        if not provided_major_data_streams:
            # The field contained [], or something that was not a list, but it was corrected to [] to satisfy model
            incompatible_assets.malformed.append(consumed_asset)
            continue

        if required_data_stream_major > max(provided_major_data_streams):
            incompatible_assets.outdated.append(consumed_asset)
        elif required_data_stream_major < min(provided_major_data_streams):
            incompatible_assets.too_new.append(consumed_asset)
        else:
            # Since the `provided_data_vers` is a list of values, it is possible that the asset provide, e.g., 4.0
            # and 6.0,  but the leapp consumes 5.0, thus we need to be careful when to say that an asset is too
            # new/outdated/none.
            incompatible_assets.unknown.append(consumed_asset)

    report_incompatible_assets(incompatible_assets)
    report_malformed_assets(incompatible_assets.malformed)
