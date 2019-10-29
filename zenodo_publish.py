#!/usr/bin/env python
import requests
import argparse
import logging
import sys
import os


BASE_URL = 'https://zenodo.org'
BASE_SANDBOX_URL = 'https://sandbox.zenodo.org'


def get_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s [zenodo_publish] %(levelname)s %(message)s')
    logging_fh = logging.FileHandler(os.path.join(os.getcwd(), 'zenodo_tools.log'))
    logging_fh.setFormatter(formatter)
    logger.addHandler(logging_fh)
    logging_stdout = logging.StreamHandler(sys.stdout)
    logging_stdout.setFormatter(formatter)
    logger.addHandler(logging_stdout)
    return logger


def main():
    parser = argparse.ArgumentParser(description='CAMI Zenodo publish tool')
    parser.add_argument('logfile', help='Log file containing deposition IDs', nargs=1)
    parser.add_argument('--zenodo_token', help='Zenodo access token', required=True)
    parser.add_argument('--sandbox', help='Sandbox test', action='store_true')
    args = parser.parse_args()

    publish_logger = get_logger()

    with open(args.logfile[0], 'r') as f:
        ids = [line.strip() for line in f if len(line.strip()) > 0]

    zenodo_url = BASE_SANDBOX_URL if args.sandbox else BASE_URL

    for id in ids:
        publish_logger.info('Publishing deposition {}'.format(id))
        r = requests.post('{}/api/deposit/depositions/{}/actions/publish'.format(zenodo_url, id),
                            params={'access_token': args.zenodo_token})
        if r.status_code == 202:
            publish_logger.info('Deposition {} published successfully'.format(id))
            print(r.json())
        elif r.status_code == 500:
            publish_logger.critical('Something went wrong. Status code: {}'.format(r.status_code))
        else:
            publish_logger.critical('Error. Status code: {}. {}'.format(r.status_code, r.json()))


if __name__ == "__main__":
    main()
