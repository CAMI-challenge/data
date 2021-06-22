#!/usr/bin/env python
import requests
import os
import argparse
import logging
import sys
from datetime import datetime
from tqdm import tqdm
from tqdm.utils import CallbackIOWrapper


BASE_URL = 'https://zenodo.org'
BASE_SANDBOX_URL = 'https://sandbox.zenodo.org'


def set_loggers():
    logger = logging.getLogger('zenodo_upload')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s [zenodo_upload] %(levelname)s %(message)s')
    logging_fh = logging.FileHandler(os.path.join(os.getcwd(), 'zenodo_tools.log'))
    logging_fh.setFormatter(formatter)
    logger.addHandler(logging_fh)
    logging_stdout = logging.StreamHandler(sys.stdout)
    logging_stdout.setFormatter(formatter)
    logger.addHandler(logging_stdout)

    logger = logging.getLogger('zenodo_deposits')
    logger.setLevel(logging.INFO)
    logging_fh = logging.FileHandler(os.path.join(os.getcwd(), 'zenodo_deposits_{:%Y%m%d_%H%M%S}.log'.format(datetime.now())))
    logger.addHandler(logging_fh)


def upload(deposition_id, file, access_token, url):
    logging.getLogger('zenodo_upload').info('Uploading {}'.format(file))

    file_name = os.path.basename(file)

    r = requests.get('{}/api/deposit/depositions/{}'.format(url, deposition_id),
                     params={'access_token': access_token})
    bucket_url = r.json()['links']['bucket']

    with open(file, 'rb') as fp:
        with tqdm(total=os.stat(file).st_size, unit="B", unit_scale=True, unit_divisor=1024) as t:
            wrapped_file = CallbackIOWrapper(t.update, fp, 'read')
            r = requests.put(
                '%s/%s' % (bucket_url, file_name),
                data=wrapped_file,
                params={'access_token': access_token},
    )

    if r.status_code >= 400:
        if r.status_code == 500:
            logging.getLogger('zenodo_upload').critical('An error occurred while uploading {}. Status code: {}.)'.format(file, r.status_code))
        else:
            logging.getLogger('zenodo_upload').critical('An error occurred while uploading {}. Status code: {}. {})'.format(file, r.status_code, r.json()))
        exit(1)
    logging.getLogger('zenodo_upload').info('Check your upload at {}/deposit/{}'.format(url, deposition_id))


def main():
    parser = argparse.ArgumentParser(description='Upload a single file to a Zenodo deposition')
    parser.add_argument('--file', help='File to be uploaded', required=True)
    parser.add_argument('--zenodo_token', help='Zenodo access token', required=True)
    parser.add_argument('--deposition_id', help='Zenodo deposition id', required=True)
    parser.add_argument('--sandbox', help='Sandbox test', action='store_true')
    args = parser.parse_args()

    set_loggers()

    upload(args.deposition_id,
           args.file,
           args.zenodo_token,
           BASE_SANDBOX_URL if args.sandbox else BASE_URL)


if __name__ == "__main__":
    main()
