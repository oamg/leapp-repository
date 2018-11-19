import logging
from leapp.libraries.actor.scanner import load_tasks_file, load_tasks


def test_load_tasks(tmpdir):
   tmpdir.join('to_install').write('a\n b\n  c \n\n\nc\na\nc\nb')
   tmpdir.join('to_keep').write('a\n b\n  c \n\n\nc\na\nc\nb')
   tmpdir.join('to_remove').write('a\n b\n  c \n\n\nc\na\nc\nb')
   m = load_tasks(tmpdir.strpath, logging)
   assert set(m.to_install) == set(['a', 'b', 'c'])
   assert set(m.to_keep) == set(['a', 'b', 'c'])
   assert set(m.to_remove) == set(['a', 'b', 'c'])


def test_load_tasks_file(tmpdir):
   f = tmpdir.join('to_install')
   f.write('a\n b\n  c \n\n\nc\na\nc\nb')
   assert set(load_tasks_file(f.strpath, logging)) == set(['a', 'b', 'c'])
   f = tmpdir.join('to_keep')
   f.write(' ')
   assert set(load_tasks_file(f.strpath, logging)) == set([])
