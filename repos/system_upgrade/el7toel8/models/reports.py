from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class Report(Model):
    topic = SystemInfoTopic

    severity = fields.StringEnum(choices=['Info',
                                          'Warning',
                                          'Error'])

    result = fields.StringEnum(choices=['Not Applicable',
                                        'Fixed',
                                        'Pass',
                                        'Fail'])

    summary = fields.String()
    details = fields.String()
    solutions = fields.Nullable(fields.String())


class CheckResult(Report):
    pass


class FinalReport(Report):
    pass


class Inhibitor(Report):
    """
    Use this model to inhibit the upgrade in the Report phase.
    """
    severity = fields.StringEnum(choices=['Error'], default='Error')
    result = fields.StringEnum(choices=['Fail'], default='Fail')
