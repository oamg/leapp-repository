import os

from leapp import reporting

CUSTOM_NETWORK_SCRIPTS = [
    "/sbin/ifup-local",
    "/sbin/ifup-pre-local",
    "/sbin/ifdown-local",
    "/sbin/ifdown-pre-local",
]
DOC_URL = "https://red.ht/upgrading-RHEL-8-to-RHEL-9-network-scripts"


def generate_report(existing_custom_network_scripts):
    """ Generate reports informing user about possible manual intervention required """

    # Show documentation url if custom network-scripts detected
    title = "custom network-scripts detected"
    summary = (
        "RHEL 9 does not support the legacy network-scripts package that was"
        " deprecated in RHEL 8. Custom network-scripts have been detected."
    )

    reporting.create_report(
        [
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Remediation(
                hint=(
                    "Migrate the custom network-scripts to NetworkManager dispatcher"
                    " scripts manually before the ugprade. Follow instructions in the"
                    " official documentation."
                )
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.NETWORK, reporting.Groups.SERVICES]),
            reporting.ExternalLink(
                title=(
                    "Upgrading from RHEL 8 to 9 - migrating custom network-scripts to"
                    " NetworkManager dispatcher scripts"
                ),
                url=DOC_URL,
            ),
        ]
        + [
            reporting.RelatedResource("file", fname)
            for fname in existing_custom_network_scripts
        ]
    )


def process():
    existing_custom_network_scripts = [
        fname for fname in CUSTOM_NETWORK_SCRIPTS if os.path.isfile(fname)
    ]
    if existing_custom_network_scripts:
        generate_report(existing_custom_network_scripts)
