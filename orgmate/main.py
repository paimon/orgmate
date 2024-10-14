from argparse import ArgumentParser
from pathlib import Path

import logging
import os

from orgmate.cli import CLI


logger = logging.getLogger(__name__)


def parse_args():
    parser = ArgumentParser()
    default_dir = os.environ.get('ORGMATE_DIR', '~/.orgmate')
    parser.add_argument('-d', '--dir', default=default_dir)
    parser.add_argument('-c', '--clear-state', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()
    dir = Path(args.dir).expanduser()
    dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    os.chdir(dir)
    logger.debug('Current working directory is %s', dir)
    CLI(args.clear_state).cmdloop()


if __name__ == '__main__':
    main()
