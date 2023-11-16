from leapp.libraries.actor import checkcustommodifications
from leapp.models import CustomModifications, Report


def test_report_any_modifications(current_actor_context):
    discovered_msgs = [CustomModifications(filename='some/changed/leapp/actor/file',
                                           type='modified',
                                           actor_name='an_actor',
                                           component='repository'),
                       CustomModifications(filename='some/new/actor/in/leapp/dir',
                                           type='custom',
                                           actor_name='a_new_actor',
                                           component='repository'),
                       CustomModifications(filename='some/new/actor/in/leapp/dir',
                                           type='modified',
                                           actor_name='a_new_actor',
                                           component='configuration'),
                       CustomModifications(filename='some/changed/file/in/framework',
                                           type='modified',
                                           actor_name='',
                                           component='framework')]
    for msg in discovered_msgs:
        current_actor_context.feed(msg)
    current_actor_context.run()
    reports = current_actor_context.consume(Report)
    assert len(reports) == 3
    assert (reports[0].report['title'] ==
            'Detected custom leapp actors or files.')
    assert 'some/new/actor/in/leapp/dir (Actor: a_new_actor)' in reports[0].report['summary']
    assert (reports[1].report['title'] ==
            'Detected modified configuration files in leapp configuration directories.')
    assert (reports[2].report['title'] ==
            'Detected modified files of the in-place upgrade tooling.')
    assert 'some/changed/file/in/framework' in reports[2].report['summary']
    assert 'some/changed/leapp/actor/file (Actor: an_actor)' in reports[2].report['summary']
