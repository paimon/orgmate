from dataclasses import dataclass
from datetime import timedelta
from functools import cache
from tempfile import NamedTemporaryFile

import os
import re
import shlex
import subprocess

from orgmate.task import StatusInvariantViolation


DEFAULT_EDITOR = '/usr/bin/vim'
CMD_PREFIX = 'do_'
PARSER_TEMPLATE = 'make_{}_parser'
HELP_TEMPLATE = 'help_{}'
DURATION_REGEX = re.compile(r'((?P<days>\d+)d)?\s*((?P<hours>\d+):(?P<minutes>\d+))?')


class NodeIndexError(Exception):
    pass


@dataclass
class Column:
    width: int = 0
    align: str = '<'

    def get_template(self):
        return '{:' + f'{self.align}{self.width}' + '}'


class Table:
    def __init__(self, col_count):
        self.cols = [Column() for _ in range(col_count)]
        self.rows = []

    def add_row(self, *row):
        row = [str(field) for field in row]
        for field, col in zip(row, self.cols):
            col.width = max(col.width, len(field))
        self.rows.append(row)

    def print(self, file=None):
        template = ' '.join(col.get_template() for col in self.cols)
        for row in self.rows:
            print(template.format(*row), file=file)
        self.rows.clear()


def _make_cmd_guard(cmd_handler, parser_factory):
    def result(cli, args):
        parser = parser_factory(cli)
        ars_list = shlex.split(args)
        try:
            args = parser.parse_args(ars_list)
        except SystemExit:
            return
        try:
            return cmd_handler(cli, args)
        except NodeIndexError:
            print('Node index out of range')
        except StatusInvariantViolation:
            print('Status invariant violation')
    return result


def _make_helper(parser_factory):
    def result(cli):
        parser = parser_factory(cli)
        message = parser.format_help()
        print(message, end='')
    return result


def add_cmd_guards(cls):
    for attr in dir(cls):
        if not attr.startswith(CMD_PREFIX):
            continue
        cmd_handler = getattr(cls, attr)
        cmd_name = attr.removeprefix(CMD_PREFIX)
        parser_attr = PARSER_TEMPLATE.format(cmd_name)
        if not hasattr(cls, parser_attr):
            continue
        parser_factory = cache(getattr(cls, parser_attr))
        setattr(cls, attr, _make_cmd_guard(cmd_handler, parser_factory))
        setattr(cls, HELP_TEMPLATE.format(cmd_name), _make_helper(parser_factory))
    return cls


def edit_text(text):
    with NamedTemporaryFile(mode='w', delete_on_close=False) as f:
        f.write(text)
        f.close()
        editor = os.environ.get('EDITOR', DEFAULT_EDITOR)
        if subprocess.run([editor, f.name]).returncode:
            return text
        with open(f.name, mode='r') as new_f:
            return new_f.read()


def parse_duration(duration_str):
    match = DURATION_REGEX.search(duration_str)
    kwargs = {key: int(value) for key, value in match.groupdict('0').items()}
    return timedelta(**kwargs)
