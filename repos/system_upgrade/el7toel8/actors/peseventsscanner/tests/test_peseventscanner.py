from leapp.snactor.fixture import current_actor_context
# from leapp.models import RpmTransactionTasks, InstalledRedHatSignedRPM, RPM


#FIXME: later...
# # https://github.com/oamg/leapp-repository/issues/22
def test_actor_execution(current_actor_context):
    pass
    # current_actor_context.run()
    #assert current_actor_context.consume(RpmTransactionTasks)
    #assert len(current_actor_context.consume(RpmTransactionTasks)) == 1
    #assert len(current_actor_context.consume(RpmTransactionTasks)[0].to_install) > 0
    #assert len(current_actor_context.consume(RpmTransactionTasks)[0].to_remove) > 0
    #assert len(current_actor_context.consume(RpmTransactionTasks)[0].to_keep) == 0

