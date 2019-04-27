from leapp.actors import Actor
from leapp.libraries.common.reporting import report_generic
from leapp.models import Report, CupsFiltersModel
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag

"""
cups-browsed configuration directory
"""

CONFDIR = '/etc/cups/'

"""
Configuration file name
"""

config = 'cups-browsed.conf'

"""
Directives to be added
"""

directives = [
              'LocalQueueNamingRemoteCUPS RemoteName', 
              'CreateIPPPrinterQueues All'
             ]

class CupsfiltersMigrate(Actor):
    """
    Actor for migrating package cups-filters.

    Migrating cups-filters package means adding two directives into
    /etc/cups/cups-browsed.conf - LocalQueueNamingRemoteCUPS and
    CreateIPPPrinterQueues.

    LocalQueueNamingRemoteCUPS directive indicates what will be used as a name
    for local print queue creation - the default is DNS-SD ID of advertised
    print queue now, it was the name of remote print queue in the past.

    CreateIPPPrinterQueues directive serves for telling cups-browsed to create
    local print queues for all available IPP printers.
    """

    name = 'cupsfilters_migrate'
    consumes = (CupsFiltersModel,)
    produces = (Report,)
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def insert_strings_into_file(self, stringed_list, filename):
      """
      insert_strings_into_file

      parameters:
      - stringed_list - list of strings
      - filename - string

      returns boolean
      """
      path = CONFDIR + filename
      with open(path, 'a') as opened_conf_file:
        opened_conf_file.write('\n')
        for string in stringed_list:
          opened_conf_file.write(string)
          opened_conf_file.write('\n')
        return True
      return False

    def process(self):
      for i in self.consume(CupsFiltersModel):
        migrateable = i.migrateable

      done = False

      if migrateable is True:
        done = self.insert_strings_into_file(directives, config)
        if done is True:
          report_generic(
                          title='Package cups-filters was migrated',
                          summary='Directives were succesfully added.',
                          severity='medium'
                        )
        else:
          report_generic(
                          title='Package cups-filters could not be migrated',
                          summary='Directives could not be add due error.',
                          severity='medium'
                        )
