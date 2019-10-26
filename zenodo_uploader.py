#!/usr/bin/env python

import requests
import json
import os
import argparse
import pandas as pd


BASE_URL = 'https://sandbox.zenodo.org'
BASE_SANDBOX_URL = 'https://sandbox.zenodo.org'
DESCRIPTION_FILE = 'description.txt'
ASSEMBLY = 'assembly.tsv'
GENOME_BINNING = 'genome_binning.tsv'
TAXONOMIC_BINNING = 'taxonomic_binning.tsv'
TAXONOMIC_PROFILING = 'taxonomic_profiling.tsv'
DESCRIPTION = 'description'
PROPERTIES = {ASSEMBLY: {DESCRIPTION: 'assembly'},
              GENOME_BINNING: {DESCRIPTION: 'genome binning'},
              TAXONOMIC_BINNING: {DESCRIPTION: 'taxonomic binning'},
              TAXONOMIC_PROFILING: {DESCRIPTION: 'taxonomic profiling'}}
TASKS = [ASSEMBLY, GENOME_BINNING, TAXONOMIC_BINNING, TAXONOMIC_PROFILING]
COMMON_FIELDS = ['Software', 'Version', 'DOI', 'DirectLink', 'FileName', 'Creator', 'ORCID', 'Affiliation']


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
    print(filtered_path_to_files)
    exit()
    return filtered_path_to_files


def get_metadata_list(path, file, properties, dataset_description):
    """
    Create metadata dictionary for each row of a tsv file with DOI == new
    :param path:
    :param file:
    :param properties:
    :param dataset_description:
    :return:
    """
    df = pd.read_csv(os.path.join(path, file), sep='\t')
    df = df[df['DOI'].str.lower() == 'new']

    if df.empty:
        return None

    metadata_list = []
    for index, row in df.iterrows():
        title = ' '.join([row['Software'], row['Version'], properties[DESCRIPTION], 'of the', dataset_description])

        row_copy= row.copy().drop(COMMON_FIELDS).dropna()
        if 'Description' in row_copy.index:
            description = row_copy.pop('Description') + '\n'
        else:
            description = ''
        for item in row_copy.iteritems():
            description = description + str(item[0]) + ': ' + str(item[1]) + '\n'

        creator_list = row['Creator'].split(';')
        affiliation_list = row['Affiliation'].split(';')
        creators_metadata = []
        if len(creator_list) == len(affiliation_list):
            for creator, affiliation in zip(creator_list, affiliation_list):
                creators_metadata.append({'name': creator, 'affiliation': affiliation})
        else:
            for creator in creator_list:
                creators_metadata.append({'name': creator, 'affiliation': affiliation_list[0]})

        metadata = {
            'metadata': {
                'title': title,
                'upload_type': 'dataset',
                'communities': [{'identifier': 'cami'}],
                'description': description,
                'creators': creators_metadata
                },
            'files': row['FileName']
            }
        metadata_list.append(metadata)
    return metadata_list


def get_deposition_id(metadata, url, access_token):
    headers = {'Content-Type': 'application/json'}
    r = requests.post('{}/api/deposit/depositions/'.format(url),
                      params={'access_token': access_token},
                      data=json.dumps({'metadata': metadata['metadata']}),
                      json={},
                      headers=headers)
    print(r.status_code)
    return str(r.json()['id'])


def upload(deposition_id, metadata, files_dir, files_in_dir, access_token, url):
    files_to_upload = metadata.pop('files').split(';')

    for file in files_to_upload:
        if file not in files_in_dir:
            print('File {} not found'.format(file))
            continue

        data = {'filename': file}
        upload_file = {'file': open(os.path.join(files_dir, file), 'rb')}
        print('Uploading {}'.format(file))
        r = requests.post('{}/api/deposit/depositions/{}/files'.format(url, deposition_id),
                          params={'access_token': access_token},
                          data=data,
                          files=upload_file)
        print(r.status_code)
    print('Check your upload at {}/record/{}'.format(url, deposition_id))


def start(path, medata_files, files_dir, files, access_token, url):
    with open(os.path.join(path, DESCRIPTION_FILE)) as f:
        dataset_description = f.readline().strip()

    for file in medata_files:
        if file not in TASKS:
            continue

        properties = PROPERTIES[file]
        metadata_list = get_metadata_list(path, file, properties, dataset_description)

        if not metadata_list:
            continue
        for metadata in metadata_list:
            deposition_id = get_deposition_id(metadata, url, access_token)
            upload(deposition_id, metadata, files_dir, files, access_token, url)


def main():
    parser = argparse.ArgumentParser(description='CAMI Zenodo uploader')
    parser.add_argument('--github_dir', help='GitHub directory', required=True)
    parser.add_argument('--files_dir', help='Directory containing files to be uploaded', required=True)
    parser.add_argument('--token', help='Zenodo access token', required=True)
    parser.add_argument('--sandbox', help='Sandbox test', action='store_true')
    args = parser.parse_args()

    path_to_github_files = get_path_to_github_files(args.github_dir)
    upload_files = os.listdir(args.files_dir)
    for path in path_to_github_files:
        start(path,
              path_to_github_files[path],
              args.files_dir,
              upload_files,
              args.token,
              BASE_SANDBOX_URL if args.sandbox else BASE_URL)


if __name__ == "__main__":
    main()
