from argparse import ArgumentParser
from cmd import Cmd
from pathlib import Path

import getpass
import os

from orgmate.task import Task


class OrgMate(Cmd):
    def _select_task(self, task):
        self.task = task
        self.prompt = f'{task.name} > '

    def preloop(self):
        self.root = Task(getpass.getuser())
        self._select_task(self.root)

    def do_add(self, arg):
        subtask = Task(arg)
        self.task.append_subtask(subtask)

    def do_list(self, arg):
        for task in self.task.subtasks:
            print(task.name)

    def do_EOF(self, arg):
        return True


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-d', '--dir', default='~/.orgmate')
    return parser.parse_args()


def main():
    args = parse_args()
    dir = Path(args.dir).expanduser()
    dir.mkdir(parents=True, exist_ok=True)
    os.chdir(dir)
    OrgMate().cmdloop()


if __name__ == '__main__':
    main()
