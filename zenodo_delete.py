#!/usr/bin/env python
import requests
import argparse
import logging
import sys


BASE_URL = 'https://zenodo.org'
BASE_SANDBOX_URL = 'https://sandbox.zenodo.org'


def get_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    logging_stdout = logging.StreamHandler(sys.stdout)
    logging_stdout.setFormatter(formatter)
    logger.addHandler(logging_stdout)
    return logger


def main():
    parser = argparse.ArgumentParser(description='CAMI Zenodo delete tool (delete unpublished depositions)')
    parser.add_argument('logfile', help='Log file containing deposition IDs', nargs=1)
    parser.add_argument('--zenodo_token', help='Zenodo access token', required=True)
    parser.add_argument('--sandbox', help='Sandbox test', action='store_true')
    args = parser.parse_args()

    delete_logger = get_logger()

    with open(args.logfile[0], 'r') as f:
        ids = [line.strip() for line in f if len(line.strip()) > 0]

    zenodo_url = BASE_SANDBOX_URL if args.sandbox else BASE_URL

    for id in ids:
        delete_logger.info('Deleting deposition {}'.format(id))
        r = requests.delete('{}/api/deposit/depositions/{}'.format(zenodo_url, id),
                            params={'access_token': args.zenodo_token})
        if r.status_code == 204:
            delete_logger.info('Deposition {} successfully deleted'.format(id))
        else:
            delete_logger.critical('Something went wrong. Status code: {}'.format(r.status_code))


if __name__ == "__main__":
    main()
