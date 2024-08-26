from argparse import ArgumentParser
from pathlib import Path

import os
from orgmate.cli import CLI


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-d', '--dir', default='~/.orgmate')
    parser.add_argument('-c', '--clear-state', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()
    dir = Path(args.dir).expanduser()
    dir.mkdir(parents=True, exist_ok=True)
    os.chdir(dir)
    CLI(args.clear_state).cmdloop()


if __name__ == '__main__':
    main()
