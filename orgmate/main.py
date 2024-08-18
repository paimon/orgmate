from argparse import ArgumentParser
from cmd import Cmd
from pathlib import Path

import logging
import os


logger = logging.getLogger(__name__)


class OrgMate(Cmd):
    def do_EOF(self, arg):
        return True


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-d', '--dir', default='~/.orgmate')
    parser.add_argument('-v', '--verbose', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    dir = Path(args.dir).expanduser()
    dir.mkdir(parents=True, exist_ok=True)
    os.chdir(dir)
    OrgMate().cmdloop()


if __name__ == '__main__':
    main()
