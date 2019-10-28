#!/usr/bin/env python
import requests
import json
import os
import argparse
import pandas as pd
import logging
import sys
from datetime import datetime


BASE_URL = 'https://zenodo.org'
BASE_SANDBOX_URL = 'https://sandbox.zenodo.org'
DESCRIPTION_FILE = 'description.txt'
TASKS_FILE = 'tasks.tsv'
DESCRIPTION = 'description'
COMMON_FIELDS = ['Software', 'Version', 'DOI', 'DirectLink', 'FileName', 'SamplesUsed', 'Creator', 'ORCID', 'Affiliation']
KEYWORDS = ['metagenomics']


def set_loggers():
    logger = logging.getLogger('zenodo_upload')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    logging_fh = logging.FileHandler(os.path.join(os.getcwd(), 'zenodo_upload.log'))
    logging_fh.setFormatter(formatter)
    logger.addHandler(logging_fh)
    logging_stdout = logging.StreamHandler(sys.stdout)
    logging_stdout.setFormatter(formatter)
    logger.addHandler(logging_stdout)

    logger = logging.getLogger('zenodo_deposits')
    logger.setLevel(logging.INFO)
    logging_fh = logging.FileHandler(os.path.join(os.getcwd(), 'zenodo_deposits_{:%Y%m%d_%H%M%S}.log'.format(datetime.now())))
    logger.addHandler(logging_fh)


def load_tasks(github_dir):
    task_file_path = os.path.join(github_dir, TASKS_FILE)
    if not os.path.isfile(task_file_path):
        logging.getLogger('zenodo_upload').critical('File {} not found. Check parameter --github_dir.'.format(task_file_path))
        exit(1)
    task = {}
    with open(task_file_path, 'r') as f:
        for line in f:
            if len(line.strip()) == 0:
                continue
            columns = line.split('\t')
            task[columns[0]] = columns[1].rstrip()
    return task


def get_path_to_github_files(github_dir):
    """
    Search local github directory recursively for subdirectories containing metadata files
    (description.txt and tsv files)
    :param github_dir:
    :return:
    """
    path_to_files = {}
    for r, d, f in os.walk(github_dir):
        if '.git' in r or '_tutorial' in r:
            continue
        for folder in d:
            if folder == '.git' or folder == '_tutorial':
                continue
            path = os.path.join(r, folder)
            path_to_files[path] = os.listdir(path)
    filtered_path_to_files = {}
    for path in path_to_files:
        if DESCRIPTION_FILE in path_to_files[path]:
            filtered_path_to_files[path] = path_to_files[path]
    return filtered_path_to_files


def get_creators_metadata(row):
    creator_list = row['Creator'].split(';')
    affiliation_list = row['Affiliation'].split(';') if pd.notna(row['Affiliation']) else []
    orcid_list = row['ORCID'].split(';') if pd.notna(row['ORCID']) else []
    creators_metadata = []
    if len(creator_list) == len(affiliation_list):
        if orcid_list:
            for creator, affiliation, orcid in zip(creator_list, affiliation_list, orcid_list):
                creators_metadata.append({'name': creator, 'affiliation': affiliation, 'orcid': orcid})
        else:
            for creator, affiliation in zip(creator_list, affiliation_list):
                creators_metadata.append({'name': creator, 'affiliation': affiliation})
    else:
        if orcid_list:
            if len(creator_list) != len(orcid_list):
                logging.getLogger('zenodo_upload').critical('The number of Creators and ORCIDs do not match')
                exit(1)
            for creator, orcid in zip(creator_list, orcid_list):
                if affiliation_list:
                    creators_metadata.append({'name': creator, 'affiliation': affiliation_list[0], 'orcid': orcid})
                else:
                    creators_metadata.append({'name': creator, 'orcid': orcid})
        else:
            for creator in creator_list:
                if affiliation_list:
                    creators_metadata.append({'name': creator, 'affiliation': affiliation_list[0]})
                else:
                    creators_metadata.append({'name': creator})
    return creators_metadata


def get_metadata_list(path, file, task_description, dataset_description):
    """
    Create metadata dictionary for each row of a tsv file with DOI == new
    :param path:
    :param file:
    :param task_description:
    :param dataset_description:
    :return:
    """
    df = pd.read_csv(os.path.join(path, file), sep='\t')

    for column in COMMON_FIELDS:
        if column not in df.columns:
            logging.getLogger('zenodo_upload').critical('File {} is missing column {}'.format(os.path.join(path, file), column))
            exit(1)

    df = df[(df['DOI'].str.lower() == 'new') | (df['DOI'].isna())]
    if df.empty:
        return None

    metadata_list = []
    for index, row in df.iterrows():
        title = ' '.join([row['Software'], row['Version'], task_description, 'of the', dataset_description + ', samples ' + row['SamplesUsed']])

        row_copy= row.copy().drop(COMMON_FIELDS).dropna()
        if 'Description' in row_copy.index:
            description = row_copy.pop('Description')
        else:
            description = ''
        for item in row_copy.iteritems():
            if len(description) > 0:
                description = description + '<br>'
            description = description + str(item[0]) + ': ' + str(item[1])

        creators_metadata = get_creators_metadata(row)
        metadata = {
            'metadata': {
                'title': title,
                'upload_type': 'dataset',
                'communities': [{'identifier': 'cami'}],
                'description': description,
                'creators': creators_metadata,
                'access_right': 'open',
                'license': 'cc-by',
                'version': row['Version'],
                'keywords': KEYWORDS
                },
            'files': row['FileName']
            }
        metadata_list.append(metadata)
    return metadata_list


def get_deposition_id(metadata, url, access_token):
    headers = {'Content-Type': 'application/json'}
    r = requests.post('{}/api/deposit/depositions'.format(url),
                      params={'access_token': access_token},
                      data=json.dumps({'metadata': metadata['metadata']}),
                      json={},
                      headers=headers)
    if r.status_code >= 400:
        logging.getLogger('zenodo_upload').critical('An error occurred while creating deposition ID. Status code: {}. {}'.format(r.status_code, r.json()))
        exit(1)
    return str(r.json()['id'])


def upload_files_exist(metadata, files_in_dir):
    files_to_upload = metadata['files'].split(';')
    for file in files_to_upload:
        if file not in files_in_dir:
            logging.getLogger('zenodo_upload').warning('Skipping {}. Reason: file {} not found'.format(metadata['metadata']['title'], file))
            return False
    return True


def upload(deposition_id, metadata, files_dir, access_token, url):
    files_to_upload = metadata.pop('files').split(';')
    for file in files_to_upload:
        logging.getLogger('zenodo_upload').info('Uploading {}'.format(os.path.join(files_dir, file)))

        data = {'filename': file}
        upload_file = {'file': open(os.path.join(files_dir, file), 'rb')}

        r = requests.post('{}/api/deposit/depositions/{}/files'.format(url, deposition_id),
                          params={'access_token': access_token},
                          data=data,
                          files=upload_file)
        if r.status_code >= 400:
            logging.getLogger('zenodo_upload').critical('An error occurred while uploading {}. Status code: {}. {})'.format(file, r.status_code, r.json()))
            exit(1)
    logging.getLogger('zenodo_upload').info('Check your upload at {}/deposit/{}'.format(url, deposition_id))


def start(path, metadata_files, files_dir, files, task, access_token, url):
    with open(os.path.join(path, DESCRIPTION_FILE)) as f:
        dataset_description = f.readline().strip()

    for file in metadata_files:
        if file not in task:
            continue
        logging.getLogger('zenodo_upload').info('Checking file {}'.format(os.path.join(path, file)))

        metadata_list = get_metadata_list(path, file, task[file], dataset_description)

        if not metadata_list:
            continue

        for metadata in metadata_list:
            if not upload_files_exist(metadata, files):
                continue
            deposition_id = get_deposition_id(metadata, url, access_token)
            logging.getLogger('zenodo_deposits').info(deposition_id)
            upload(deposition_id, metadata, files_dir, access_token, url)


def main():
    parser = argparse.ArgumentParser(description='CAMI Zenodo upload tool')
    parser.add_argument('--github_dir', help='GitHub directory [default: current working directory]', required=False)
    parser.add_argument('--files_dir', help='Directory containing files to be uploaded', required=True)
    parser.add_argument('--zenodo_token', help='Zenodo access token', required=True)
    parser.add_argument('--sandbox', help='Sandbox test', action='store_true')
    args = parser.parse_args()

    set_loggers()
    github_dir = args.github_dir if args.github_dir else os.getcwd()
    task = load_tasks(github_dir)
    path_to_github_files = get_path_to_github_files(github_dir)
    upload_files = os.listdir(args.files_dir)
    for path in path_to_github_files:
        start(path,
              path_to_github_files[path],
              args.files_dir,
              upload_files,
              task,
              args.zenodo_token,
              BASE_SANDBOX_URL if args.sandbox else BASE_URL)


if __name__ == "__main__":
    main()
