from argparse import ArgumentParser
from cmd import Cmd

import getpass
import shelve
import shlex

from orgmate.table import Table
from orgmate.task import Flow, State, StateInvariantViolation, Task


class NodeIndexError(Exception):
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
            except NodeIndexError:
                print('Node index out of range')
            except StateInvariantViolation:
                print('State invariant violation')
        return result


def make_helper(parser):
    def result(_):
        message = parser.format_help()
        print(message, end='')
    return result


def make_parser(prog):
    result = ArgumentParser(prog=prog)
    result.add_argument('node_index', type=int, nargs='?')
    return result


def make_add_parser():
    result = ArgumentParser(prog='add')
    result.add_argument('task_name', nargs='+')
    group = result.add_mutually_exclusive_group()
    group.add_argument('-b', '--before', type=int)
    group.add_argument('-i', '--index', type=int)
    return result


def make_tree_parser():
    result = ArgumentParser(prog='tree')
    result.add_argument('-d', '--depth', type=int)
    result.add_argument('node_index', type=int, nargs='?')
    return result


def make_rm_parser():
    result = ArgumentParser(prog='rm')
    result.add_argument('node_index', type=int, nargs='+')
    return result


def make_ln_parser():
    result = ArgumentParser(prog='ln')
    result.add_argument('-b', '--before', action='store_true')
    result.add_argument('node_index', type=int, nargs='+')
    result.add_argument('dest', type=int)
    return result


def make_mv_parser():
    result = ArgumentParser(prog='mv')
    result.add_argument('-b', '--before', action='store_true')
    result.add_argument('node_index', type=int, nargs='+')
    result.add_argument('dest', type=int)
    return result


def make_set_parser():
    result = ArgumentParser(prog='set')
    result.add_argument('key', choices=['name', 'flow', 'state', 'priority', 'aggregate'])
    result.add_argument('value')
    result.add_argument('node_index', type=int, nargs='*')
    return result


class CLI(Cmd):
    def __init__(self, clear_state):
        super().__init__()
        self.clear_state = clear_state
        self.aliases = {
            'ls': 'tree -d 1',
            'restart': 'set state new',
            'activate': 'set state active',
            'suspend': 'set state inactive',
            'finish': 'set state done',
        }

    def _select_task(self, task):
        self.task = task
        self.prompt = f'{task.name} > '

    def _get_node(self, idx):
        try:
            return self.last_nodes[idx]
        except IndexError:
            raise NodeIndexError

    def preloop(self):
        self.db = shelve.open('data')
        if not self.clear_state and 'root' in self.db:
            self.root = self.db['root']
        else:
            self.root = Task(getpass.getuser(), State.ACTIVE)
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

    sel_parser = make_parser('sel')
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
        elif args.index is not None:
            add_func = self._get_node(args.index).task.add
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
        task = self.task if args.node_index is None else self._get_node(args.node_index).task
        table = Table(3)
        table.cols[0].align = '>'
        for idx, node in enumerate(task.iter_subtasks(args.depth)):
            table.add_row(idx, ' ' * node.depth * 4 + node.task.name, node.task.state.name)
            self.last_nodes.append(node)
        table.print()

    rm_parser = make_rm_parser()
    help_rm = make_helper(rm_parser)

    @cmd_guard(rm_parser)
    def do_rm(self, args):
        for idx in args.node_index:
            self._get_node(idx).remove()

    ln_parser = make_ln_parser()
    help_ln = make_helper(ln_parser)

    @cmd_guard(ln_parser)
    def do_ln(self, args):
        if args.before:
            add_func = self._get_node(args.dest).insert
        else:
            add_func = self._get_node(args.dest).task.add
        for idx in args.node_index:
            add_func(self._get_node(idx).task)

    mv_parser = make_mv_parser()
    help_mv = make_helper(mv_parser)

    @cmd_guard(mv_parser)
    def do_mv(self, args):
        if args.before:
            add_func = self._get_node(args.dest).insert
        else:
            add_func = self._get_node(args.dest).task.add
        for idx in args.node_index:
            node = self._get_node(idx)
            node.remove()
            add_func(node.task)

    set_parser = make_set_parser()
    help_set = make_helper(set_parser)

    @cmd_guard(set_parser)
    def do_set(self, args):
        value = args.value
        match args.key:
            case 'state':
                value = State[value.upper()]
            case 'flow':
                value = Flow[value.upper()]
            case 'priority':
                value = int(value)
            case 'aggregate':
                value = (value.lower() == 'true')
        if not args.node_index:
            setattr(self.task, args.key, value)
            return
        for idx in args.node_index:
            task = self._get_node(idx).task
            setattr(task, args.key, value)

    info_parser = make_parser('info')
    help_info = make_helper(info_parser)

    @cmd_guard(info_parser)
    def do_info(self, args):
        task = self.task if args.node_index is None else self._get_node(args.node_index).task
        table = Table(2)
        table.add_row('Name', task.name)
        table.add_row('State', task.state.name)
        table.add_row('Flow', task.flow.name)
        table.add_row('Priority', str(task.priority))
        table.add_row('Aggregate', str(task.aggregate))
        table.add_row('Next states', ', '.join(state.name for state in task.get_next_states()))
        table.print()

    todo_parser = make_parser('todo')
    todo_info = make_helper(todo_parser)

    @cmd_guard(todo_parser)
    def do_todo(self, args):
        task = self.task if args.node_index is None else self._get_node(args.node_index).task
        seen = set()
        self.last_nodes.clear()
        for node in task.iter_subtasks():
            task = node.task
            if task.priority <= 0 or task in seen or not task.get_next_states():
                continue
            seen.add(task)
            self.last_nodes.append(node)
        self.last_nodes.sort(key=lambda n: n.task.priority, reverse=True)
        table = Table(3)
        table.cols[0].align = '>'
        for idx, node in enumerate(self.last_nodes):
            table.add_row(str(idx), node.task.name, node.task.state.name)
        table.print()

    def do_EOF(self, _):
        return True
