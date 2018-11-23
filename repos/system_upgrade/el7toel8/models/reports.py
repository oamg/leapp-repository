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
