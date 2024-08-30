from argparse import ArgumentParser
from cmd import Cmd

import getpass
import shelve
import shlex

from orgmate.task import Task


class TaskIndexError(Exception):
    pass


class cmd_guard:
    def __init__(self, parser):
        self.parser = parser

    def __call__(self, cmd_handler):
        parser = self.parser
        def result(cli, args):
            ars_list = shlex.split(args)
            try:
                args = parser.parse_args(ars_list)
            except SystemExit:
                return
            try:
                return cmd_handler(cli, args)
            except TaskIndexError:
                print('Node index out of range')
        return result


def make_helper(parser):
    def result(_):
        message = parser.format_help()
        print(message, end='')
    return result


def make_add_parser():
    result = ArgumentParser(prog='add')
    result.add_argument('task_name', nargs='+')
    group = result.add_mutually_exclusive_group()
    group.add_argument('-b', '--before', type=int)
    group.add_argument('-n', '--node', type=int)
    return result


def make_sel_parser():
    result = ArgumentParser(prog='sel')
    result.add_argument('node_index', type=int, nargs='?')
    return result


def make_tree_parser():
    result = ArgumentParser(prog='list')
    result.add_argument('-n', '--node', type=int)
    result.add_argument('-d', '--depth', type=int)
    return result


class CLI(Cmd):
    def __init__(self, clear_state):
        super().__init__()
        self.clear_state = clear_state
        self.aliases = {
            'list': 'tree -d 1'
        }

    def _select_task(self, task):
        self.task = task
        self.prompt = f'{task.name} > '

    def _get_node(self, idx):
        try:
            return self.last_nodes[idx]
        except IndexError:
            raise TaskIndexError

    def preloop(self):
        self.db = shelve.open('state')
        if not self.clear_state and 'root' in self.db:
            self.root = self.db['root']
        else:
            self.root = Task(getpass.getuser())
        self._select_task(self.root)
        self.last_nodes = []

    def precmd(self, line):
        for key, val in self.aliases.items():
            if line.startswith(key):
                return val + line.removeprefix(key)
        return line

    def postloop(self):
        self.db['root'] = self.root
        self.db.close()

    sel_parser = make_sel_parser()
    help_sel = make_helper(sel_parser)

    @cmd_guard(sel_parser)
    def do_sel(self, args):
        if args.node_index is None:
            self._select_task(self.root)
            return
        node = self._get_node(args.node_index)
        self._select_task(node.task)

    add_parser = make_add_parser()
    help_add = make_helper(add_parser)

    @cmd_guard(add_parser)
    def do_add(self, args):
        if args.before is not None:
            add_func = self._get_node(args.before).insert
        elif args.node is not None:
            add_func = self._get_node(args.node).task.add
        else:
            add_func = self.task.add
        for name in args.task_name:
            subtask = Task(name)
            add_func(subtask)

    tree_parser = make_tree_parser()
    help_tree = make_helper(tree_parser)

    @cmd_guard(tree_parser)
    def do_tree(self, args):
        self.last_nodes.clear()
        task = self.task if args.node is None else self._get_node(args.node).task
        for idx, node in enumerate(task.iter_subtasks(args.depth)):
            print(idx, '\t'* node.depth + node.task.name)
            self.last_nodes.append(node)

    def do_del(self, arg):
        idx = int(arg) - 1
        self.last_nodes[idx].delete()

    def do_EOF(self, _):
        return True
