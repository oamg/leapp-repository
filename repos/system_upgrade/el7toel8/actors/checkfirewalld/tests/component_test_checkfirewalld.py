from leapp.models import FirewalldFacts
from leapp.reporting import Report
from leapp.utils.report import is_inhibitor


def test_actor_execution(current_actor_context):
    current_actor_context.feed(
        FirewalldFacts(firewall_config_command='',
                       ebtablesTablesInUse=['broute'],
                       ipsetTypesInUse=['hash:net,port']))
    current_actor_context.run()
    report_fileds = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fileds)
