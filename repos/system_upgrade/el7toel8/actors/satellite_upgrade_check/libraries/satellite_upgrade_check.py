import textwrap

from leapp import reporting


def satellite_upgrade_check(facts):
    if facts.postgresql.local_postgresql:
        if facts.postgresql.old_var_lib_pgsql_data:
            title = "Old PostgreSQL data found in /var/lib/pgsql/data"
            summary = """
            The upgrade wants to move PostgreSQL data to /var/lib/pgsql/data,
            but this directory already exists on your system.
            Please make sure /var/lib/pgsql/data doesn't exist prior to the upgrade.
            """
            reporting.create_report([
                reporting.Title(title),
                reporting.Summary(textwrap.dedent(summary).strip()),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups([]),
                reporting.Groups([reporting.Groups.INHIBITOR])
            ])

        title = "Satellite PostgreSQL data migration"
        flags = []
        severity = reporting.Severity.MEDIUM
        reindex_msg = textwrap.dedent("""
        After the data has been moved to the new location, all databases will require a REINDEX.
        This will happen automatically during the first boot of the system.
        """).strip()

        if facts.postgresql.same_partition:
            migration_msg = "Your PostgreSQL data will be automatically migrated."
        else:
            scl_psql_path = '/var/opt/rh/rh-postgresql12/lib/pgsql/data/'
            if facts.postgresql.space_required > facts.postgresql.space_available:
                storage_message = """You currently don't have enough free storage to move the data.
                Automatic moving cannot be performed."""
                flags = [reporting.Groups.INHIBITOR]
                severity = reporting.Severity.HIGH
            else:
                storage_message = """You currently have enough free storage to move the data.
                This operation can be performed by the upgrade process."""
            migration_msg = """
            Your PostgreSQL data in {} is currently on a dedicated volume.
            PostgreSQL on RHEL8 expects the data to live in /var/lib/pgsql/data.
            {}
            However, instead of moving the data over, you might want to consider manually adapting your mounts,
            so that the contents of {} are available in /var/lib/pgsql/data.
            """.format(scl_psql_path, storage_message, scl_psql_path)

        summary = "{}\n{}".format(textwrap.dedent(migration_msg).strip(), reindex_msg)

        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(severity),
            reporting.Groups([]),
            reporting.Groups(flags)
        ])
