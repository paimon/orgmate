from argparse import ArgumentParser

import logging


logger = logging.getLogger(__name__)


class OrgMate:
    def run(self):
        logger.debug('Hello, world!')


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    app = OrgMate()
    app.run()


if __name__ == '__main__':
    main()
