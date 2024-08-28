from argparse import ArgumentParser
from cmd import Cmd

import getpass
import shelve
import shlex

from orgmate.task import Task


def make_add_parser():
    result = ArgumentParser(prog='add')
    result.add_argument('names', nargs='+')
    group = result.add_mutually_exclusive_group()
    group.add_argument('-b', '--before', type=int)
    group.add_argument('-t', '--to', type=int)
    group.add_argument('-a', '--after', type=int)
    return result


def attach_args_parser(cmd_handler):
    def result(self, args):
        cmd = cmd_handler.__name__.removeprefix('do_')
        parser = self.args_parsers[cmd]
        try:
            args = parser.parse_args(shlex.split(args))
        except SystemExit:
            return
        return cmd_handler(self, args)
    return result


class CLI(Cmd):
    args_parsers = {
        'add': make_add_parser(),
    }

    def __init__(self, clear_state):
        super().__init__()
        self.clear_state = clear_state

    def _select_task(self, task):
        self.task = task
        self.prompt = f'{task.name} > '

    def _list_subtasks(self, max_depth=None):
        self.last_nodes.clear()
        for idx, node in enumerate(self.task.iter_subtasks(max_depth), 1):
            print(idx, '\t'* node.depth + node.task.name)
            self.last_nodes.append(node)

    def preloop(self):
        self.db = shelve.open('state')
        if not self.clear_state and 'root' in self.db:
            self.root = self.db['root']
        else:
            self.root = Task(getpass.getuser())
        self._select_task(self.root)
        self.last_nodes = []

    def postloop(self):
        self.db['root'] = self.root
        self.db.close()

    @attach_args_parser
    def do_add(self, args):
        for name in args.names:
            subtask = Task(name)
            self.task.add(subtask)

    def do_list(self, _):
        self._list_subtasks(1)

    def do_tree(self, _):
        self._list_subtasks()

    def do_sel(self, arg):
        if not arg:
            self._select_task(self.root)
            return
        idx = int(arg) - 1
        self._select_task(self.last_nodes[idx].task)

    def do_del(self, arg):
        idx = int(arg) - 1
        self.last_nodes[idx].delete()

    def do_EOF(self, _):
        return True

    def do_help(self, arg):
        if parser := self.args_parsers.get(arg):
            print(parser.format_help())
        else:
            print('Invalid command:', arg)
