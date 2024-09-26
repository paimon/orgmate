from dataclasses import dataclass
from tempfile import NamedTemporaryFile

import os
import subprocess


DEFAULT_EDITOR = '/usr/bin/vim'


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

    def edit(self):
        with NamedTemporaryFile(mode='w', delete_on_close=False) as f:
            self.print(f)
            f.close()
            editor = os.environ.get('EDITOR', DEFAULT_EDITOR)
            if subprocess.run([editor, f.name]).returncode:
                return self.rows
            with open(f.name, mode='r') as new_f:
                maxsplit = len(self.cols) - 1
                self.rows = [line.rstrip().split(maxsplit=maxsplit) for line in new_f]
                return self.rows
