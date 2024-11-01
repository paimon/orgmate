from argparse import ArgumentParser, ArgumentTypeError
from cmd import Cmd
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_time
from functools import partial

import getpass
import logging
import shelve
import shlex

from orgmate.cli_utils import (
    add_cmd_guards,
    Table,
    NodeIndexError,
    StatusInvariantViolation,
    edit_text,
    parse_duration
)
from orgmate.job import Job
from orgmate.log import Log
from orgmate.task import Flow, Status, Task, NodeFilter


logger = logging.getLogger(__name__)


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
            'ls': 'tree -d 1 -f status -f progress',
            'restart': 'set status new',
            'start': 'set status active',
            'stop': 'set status inactive',
            'finish': 'set status done',
        }
        self.last_save = datetime.now()

    def _select_task(self, task):
        self.task = task
        self.prompt = f'{datetime.now():%Y-%m-%d %H:%M}, {task.name} > '

    def _get_node(self, idx):
        try:
            return self.last_nodes[idx - 1]
        except IndexError:
            raise NodeIndexError

    def _get_task(self, node_index, default_task=None):
        if node_index is None:
            return default_task or self.task
        if node_index == 0:
            return self.task.parents[0]
        return self._get_node(node_index).task

    def _save(self):
        self.db['aliases'] = self.aliases
        self.db['root'] = self.root
        self.last_save = datetime.now()

    def preloop(self):
        self.db = shelve.open('data')
        if not self.clear_state and 'root' in self.db:
            self.root = self.db['root']
            self.aliases = self.db['aliases']
        else:
            self.root = Task(getpass.getuser())
        self._select_task(self.root)
        Job.init_schedule(self.root)
        self.last_nodes = []
        self.last_jobs = []

    def precmd(self, line):
        current_task = self.task
        for job in Job.iter_pending():
            logger.debug('Running %s', job)
            Log.current_time = job.time
            self._select_task(job.task)
            self.onecmd(job.cmd)
        else:
            Log.current_time = None
            self._select_task(current_task)
        return line

    def postcmd(self, stop, line):
        if stop or timedelta(minutes=5) < datetime.now() - self.last_save:
            self._save()
        return stop

    def postloop(self):
        self.db.close()

    def emptyline(self):
        return self.onecmd('todo')

    def default(self, line):
        for key, val in self.aliases.items():
            if line.startswith(key):
                return self.onecmd(val + line.removeprefix(key))
        super().default(line)

    def completenames(self, text, *ignored):
        aliases = [key for key in self.aliases if key.startswith(text)]
        return super().completenames(text, *ignored) + aliases

    def do_EOF(self, _):
        'Exit OrgMate'
        return True

    def do_save(self, _):
        'Save current state'
        self._save()

    make_sel_parser = lambda _: make_parser('sel')

    def do_sel(self, args):
        task = self._get_task(args.node_index, self.root)
        self._select_task(task)

    def make_add_parser(self):
        result = ArgumentParser(prog='add')
        result.add_argument('-c', '--context', action='store_true')
        result.add_argument('task_name', nargs='+')
        group = result.add_mutually_exclusive_group()
        group.add_argument('-b', '--before', type=int)
        group.add_argument('-a', '--after', type=int)
        group.add_argument('-n', '--node', type=int)
        return result

    def do_add(self, args):
        if args.before is not None:
            add_func = self._get_node(args.before).insert
        elif args.after is not None:
            add_func = partial(self._get_node(args.after).insert, after=True)
        elif args.node is not None:
            add_func = self._get_node(args.node).task.add
        else:
            add_func = self.task.add
        for name in args.task_name:
            subtask = Task(name, context_mode=args.context)
            add_func(subtask)

    def make_tree_parser(self):
        result = ArgumentParser(prog='tree')
        result.add_argument('-a', '--all', action='store_true')
        result.add_argument('-d', '--depth', type=int)
        result.add_argument('-f', '--field', action='append', choices=Task.PUBLIC_RO_FIELDS, default=[])
        result.add_argument('node_index', type=int, nargs='?')
        return result

    def do_tree(self, args):
        self.last_nodes.clear()
        task = self._get_task(args.node_index)
        table = Table(2 + len(args.field))
        table.cols[0].align = '>'
        node_filter = NodeFilter(max_depth=args.depth, skip_done=not args.all, skip_seen=False)
        for idx, node in enumerate(task.iter_subtasks(node_filter), 1):
            fields = [idx, node.get_name()]
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
        result.add_argument('-a', '--after', action='store_true')
        result.add_argument('node_index', type=int, nargs='+')
        result.add_argument('dest', type=int)
        return result

    def do_ln(self, args):
        if args.before:
            add_func = self._get_node(args.dest).insert
        elif args.after:
            add_func = partial(self._get_node(args.dest).insert, after=True)
        else:
            add_func = self._get_node(args.dest).task.add
        for idx in args.node_index:
            add_func(self._get_node(idx).task)

    def make_mv_parser(self):
        result = ArgumentParser(prog='mv')
        result.add_argument('-b', '--before', action='store_true')
        result.add_argument('-a', '--after', action='store_true')
        result.add_argument('node_index', type=int, nargs='+')
        result.add_argument('dest', type=int)
        return result

    def do_mv(self, args):
        if args.before:
            add_func = self._get_node(args.dest).insert
        elif args.after:
            add_func = partial(self._get_node(args.dest).insert, after=True)
        else:
            add_func = self._get_node(args.dest).task.add
        for idx in args.node_index:
            node = self._get_node(idx)
            node.remove()
            add_func(node.task)

    def make_set_parser(self):
        result = ArgumentParser(prog='set')
        result.add_argument('-f', '--force', action='store_true')
        result.add_argument('key', choices=Task.PUBLIC_FIELDS)
        result.add_argument('value')
        result.add_argument('node_index', type=int, nargs='*')
        return result

    def complete_set(self, text, line, *ignored):
        choices = {
            'set': Task.PUBLIC_FIELDS,
            'status': [v.name.lower() for v in Status],
            'flow': [v.name.lower() for v in Flow],
            'aggregate': ['true', 'false'],
        }
        *_, key, value = shlex.split(line)
        return [f for f in choices.get(key, []) if f.startswith(value)]

    def do_set(self, args):
        value = args.value
        try:
            match args.key:
                case 'status':
                    value = Status[value.upper()]
                case 'flow':
                    value = Flow[value.upper()]
                case 'priority':
                    value = int(value)
                case 'aggregate':
                    value = (value == 'true')
        except:
            raise ArgumentTypeError
        tasks = map(self._get_task, args.node_index) if args.node_index else [self.task]
        for t in tasks:
            if not args.force and not t.checkattr(args.key, value):
                raise StatusInvariantViolation
            setattr(t, args.key, value)

    make_info_parser = lambda _: make_parser('info')

    def do_info(self, args):
        task = self._get_task(args.node_index)
        table = Table(2)
        table.add_row('Name', task.name)
        table.add_row('Status', task.status)
        table.add_row('Flow', task.flow)
        table.add_row('Priority', str(task.priority))
        table.add_row('Aggregate', str(task.aggregate))
        table.add_row('Progress', str(task.progress))
        table.add_row('Next statuses', ', '.join(str(status) for status in task.get_next_statuses()))
        table.print()

    make_todo_parser = lambda _: make_parser('todo')

    def do_todo(self, args):
        task = self._get_task(args.node_index)
        self.last_nodes.clear()
        for node in task.iter_subtasks():
            task = node.task
            if task.priority <= 0 or not task.get_next_statuses():
                continue
            self.last_nodes.append(node)
        self.last_nodes.sort(key=lambda n: n.task.priority, reverse=True)
        table = Table(3)
        table.cols[0].align = '>'
        for idx, node in enumerate(self.last_nodes, 1):
            table.add_row(str(idx), node.task.name, node.task.status)
        table.print()

    make_log_parser = lambda _: make_parser('log')

    def do_log(self, args):
        task = self._get_task(args.node_index)
        table = Table(2)
        for item in task.log.items:
            table.add_row(item.status, item.timestamp)
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

    def make_sked_parser(self):
        result = ArgumentParser(prog='sked')
        result.add_argument('-n', '--node', type=int)
        subparsers = result.add_subparsers(dest='subcmd', required=True)
        subparsers.add_parser('ls')
        parser_add = subparsers.add_parser('add')
        parser_add.add_argument('-p', '--period', type=parse_duration)
        parser_add.add_argument('time', type=parse_time)
        parser_add.add_argument('cmd')
        parser_rm = subparsers.add_parser('rm')
        parser_rm.add_argument('job_index', type=int, nargs='+')
        return result

    def do_sked(self, args):
        task = self._get_task(args.node)
        if args.subcmd == 'add':
            Job(task, args.time, args.cmd, args.period).add()
            return
        if args.subcmd == 'rm':
            for idx in args.job_index:
                self.last_jobs[idx - 1].remove()
            return
        self.last_jobs = task.jobs.copy()
        table = Table(4)
        for idx, job in enumerate(self.last_jobs, 1):
            table.add_row(idx, job.time, job.cmd, job.period if job.period else '-')
        table.print()

    def make_note_parser(self):
        result = make_parser('note')
        result.add_argument('-e', '--edit', action='store_true')
        return result

    def do_note(self, args):
        task = self._get_task(args.node_index)
        if args.edit:
            task.note = edit_text(task.note)
        else:
            print(task.note, end='')
