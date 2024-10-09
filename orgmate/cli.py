from argparse import ArgumentParser
from cmd import Cmd

import getpass
import shelve

from orgmate.cli_utils import add_cmd_guards, Table, NodeIndexError
from orgmate.task import Flow, State, Task


def make_parser(prog):
    result = ArgumentParser(prog=prog)
    result.add_argument('node_index', type=int, nargs='?')
    return result


@add_cmd_guards
class CLI(Cmd):
    def __init__(self, clear_state):
        super().__init__()
        self.clear_state = clear_state
        self.aliases = {
            'ls': 'tree -d 1 -f state -f progress',
            'restart': 'set state new',
            'start': 'set state active',
            'stop': 'set state inactive',
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
            self.aliases = self.db['aliases']
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
        self.db['aliases'] = self.aliases
        self.db.close()

    make_sel_parser = lambda _: make_parser('sel')

    def do_sel(self, args):
        if args.node_index is None:
            self._select_task(self.root)
            return
        node = self._get_node(args.node_index)
        self._select_task(node.task)

    def make_add_parser(self):
        result = ArgumentParser(prog='add')
        result.add_argument('task_name', nargs='+')
        group = result.add_mutually_exclusive_group()
        group.add_argument('-b', '--before', type=int)
        group.add_argument('-i', '--index', type=int)
        return result

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

    def make_tree_parser(self):
        result = ArgumentParser(prog='tree')
        result.add_argument('-d', '--depth', type=int)
        result.add_argument('-f', '--field', action='append', default=[])
        result.add_argument('node_index', type=int, nargs='?')
        return result

    def do_tree(self, args):
        self.last_nodes.clear()
        task = self.task if args.node_index is None else self._get_node(args.node_index).task
        table = Table(2 + len(args.field))
        table.cols[0].align = '>'
        for idx, node in enumerate(task.iter_subtasks(args.depth)):
            fields = [idx, ' ' * node.depth * 4 + node.task.name]
            fields += [getattr(node.task, field) for field in args.field]
            table.add_row(*fields)
            self.last_nodes.append(node)
        table.print()

    def make_rm_parser(self):
        result = ArgumentParser(prog='rm')
        result.add_argument('node_index', type=int, nargs='+')
        return result

    def do_rm(self, args):
        for idx in args.node_index:
            self._get_node(idx).remove()

    def make_ln_parser(self):
        result = ArgumentParser(prog='ln')
        result.add_argument('-b', '--before', action='store_true')
        result.add_argument('node_index', type=int, nargs='+')
        result.add_argument('dest', type=int)
        return result

    def do_ln(self, args):
        if args.before:
            add_func = self._get_node(args.dest).insert
        else:
            add_func = self._get_node(args.dest).task.add
        for idx in args.node_index:
            add_func(self._get_node(idx).task)

    def make_mv_parser(self):
        result = ArgumentParser(prog='mv')
        result.add_argument('-b', '--before', action='store_true')
        result.add_argument('node_index', type=int, nargs='+')
        result.add_argument('dest', type=int)
        return result

    def do_mv(self, args):
        if args.before:
            add_func = self._get_node(args.dest).insert
        else:
            add_func = self._get_node(args.dest).task.add
        for idx in args.node_index:
            node = self._get_node(idx)
            node.remove()
            add_func(node.task)

    def make_set_parser(self):
        result = ArgumentParser(prog='set')
        result.add_argument('key', choices=['name', 'flow', 'state', 'priority', 'aggregate'])
        result.add_argument('value')
        result.add_argument('node_index', type=int, nargs='*')
        return result

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

    make_info_parser = lambda _: make_parser('info')

    def do_info(self, args):
        task = self.task if args.node_index is None else self._get_node(args.node_index).task
        table = Table(2)
        table.add_row('Name', task.name)
        table.add_row('State', task.state.name)
        table.add_row('Flow', task.flow.name)
        table.add_row('Priority', str(task.priority))
        table.add_row('Aggregate', str(task.aggregate))
        table.add_row('Progress', str(task.progress))
        table.add_row('Next states', ', '.join(state.name for state in task.get_next_states()))
        table.print()

    make_todo_parser = lambda _: make_parser('todo')

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

    make_log_parser = lambda _: make_parser('log')

    def do_log(self, args):
        task = self.task if args.node_index is None else self._get_node(args.node_index).task
        table = Table(2)
        for item in task.log.items:
            table.add_row(item.state, item.timestamp)
        table.print()

    def make_alias_parser(self):
        result = ArgumentParser(prog='alias')
        subparsers = result.add_subparsers(dest='subcmd', required=True)
        subparsers.add_parser('ls')
        parser_add = subparsers.add_parser('add')
        parser_add.add_argument('key')
        parser_add.add_argument('value')
        parser_rm = subparsers.add_parser('rm')
        parser_rm.add_argument('key', nargs='+')
        return result

    def do_alias(self, args):
        if args.subcmd == 'add':
            self.aliases[args.key] = args.value
            return
        if args.subcmd == 'rm':
            for key in args.key:
                self.aliases.pop(key, None)
            return
        table = Table(2)
        for key, value in self.aliases.items():
            table.add_row(key, value)
        table.print()

    def emptyline(self):
        return self.onecmd('todo')

    def do_EOF(self, _):
        return True
