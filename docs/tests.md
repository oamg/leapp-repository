# Tests for actors

You can implement two types of tests for an actor in the leapp-repository - component and unit tests.

## Component tests
   - These tests provide fabricated input messages for the actor, check the outputs stated in the actor's description.
   - These tests should not be written based on the actor's code but rather based on the behavior stated in the actor's description. Ideally they could be written by somebody who doesn't know the code.
   - Example of a component test: https://github.com/oamg/leapp-repository/blob/master/repos/system_upgrade/el7toel8/actors/redhatsignedrpmcheck/tests/test_redhatsignedrpmcheck.py

## Unit tests
   - These tests deal with individual actor's functions/methods.
   - You can't unit test any method/function within the actor.py. You can write unit tests only for the functions/methods within actor's libraries.
   - Thus, to be able to write unit tests for an actor, ideally the only thing in the actor.py's _process()_ method is calling the entry-point function of the actor's library python module.
   - Tutorial on how to write unit tests: https://leapp.readthedocs.io/en/latest/unit-testing.html


Both types of tests are to be placed in the actor's _tests_ folder.
