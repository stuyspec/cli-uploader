#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function
import httplib2
import os
import io
import re

from apiclient import discovery
from apiclient.http import MediaIoBaseDownload
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    parser = argparse.ArgumentParser(
        description='Automatically upload Spectator articles.',
        parents=[tools.argparser])
    parser.add_argument('--read-article', help='reads article in file')
    args = parser.parse_args()
except ImportError:
    flags = None

from colorama import init, Fore, Back, Style
init()

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/drive'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Spec-Uploader CLI'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'drive-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:  # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def getTitle(line):
    if 'Title: ' in line:
        line = line[line.find('Title: ') + len('Title: '):]
    line = line.strip()
    return raw_input(
        (Fore.GREEN + Style.BRIGHT + 'title: ' + Style.RESET_ALL +
         '({}) ').format(line)) or line  # if no user input, defaults to line

def getContributors(byline):
    if 'By:' in byline:
        byline = byline[len('By:'):]
    else:
        byline = byline[len('By'):]
    byline = re.findall(r"[\w']+|[.,!-?;]", byline.strip())
    contributors = []
    cutoff = 0
    """Looks through tokens from left to right until a separator is reached,
    then joins the previous tokens into a name. 
    """
    for i in range(0, len(byline)):
        if byline[i] in ',&' or byline[i] == 'and':
            name = cleanName(' '.join(byline[cutoff:i]))
            contributors.append(name)
            cutoff = i + 1
    contributors.append(cleanName(' '.join(
        byline[cutoff:])))  # add last contributor
    contributors = filter(None, contributors)  # removes empty strings
    byline = raw_input(
        (Fore.GREEN + Style.BRIGHT + 'contributors : ' + Style.RESET_ALL +
         '({0}) ').format(', '.join(contributors))) or byline # confirm contributors
    return contributors

def manualArticleRead(content, message):
    print(Back.RED + Fore.WHITE + Style.BRIGHT + message + Style.RESET \
          +' You have entered manual article-reading mode for headers. ' \
          + 'Input "m" to extend the article, input "f" to show the whole ' \
          + 'article, or press ENTER to continue.' + Back.RESET + Fore.RED)
    content = content.split('\n')
    lineNum = 0
    while lineNum < len(content):
        print(*content[lineNum:lineNum + 5], sep='\n')
        lineNum += 5
        showMore = raw_input()
        if showMore == 'f':
            print(*content[lineNum:], sep='\n')
        elif showMore != 'm':
            break

def readArticle(content, filename):
    data = content.split('\n')

    title = getTitle(data[0])

    # If article is a survey, skip.
    if 'survey' in filename or content.count('%') > 10:  # possibly a survey
        while True:
            surveyConfirmation = raw_input(
                (Fore.RED + Style.BRIGHT +
                 'Is this article, with {0} counts of "%", a survey? (y/n) ' +
                 Style.RESET_ALL).format(content.count('%')))
            if surveyConfirmation == 'y':
                print(Fore.RED + Style.BRIGHT + 'Survey skipped.')
                return title
            elif surveyConfirmation == 'n':
                break

    try:
        byline = next((line for line in data if line.find('By') >= 0))
    except StopIteration:  # no byline found
        manualArticleRead(content, 'No byline found.')
        byline = raw_input(Fore.GREEN + Style.BRIGHT \
                                 + 'enter contributors separated by ", ": ' \
                                 + Style.RESET_ALL)
    contributors = getContributors(byline)

    try:
        summary = next((line for line in data
                        if 'focus sentence:' in line.lower()))
        summary = summary.replace('Focus Sentence:', '').replace(
            'Focus sentence:', '').strip()
        summary = raw_input(
            (Fore.GREEN + Style.BRIGHT + 'summary/focus: ' + Style.RESET_ALL +
             '({0}) ').format(summary)) or summary
    except StopIteration:  # no focus sentence found
        print(
            Back.RED + Fore.WHITE +
            'No focus sentence found. Header text (input "m" for more header text, ENTER to progress): '
            + Back.RESET + Fore.RED)
        lineNum = 0
        while True:
            print(*data[lineNum:lineNum + 5], sep='\n')
            lineNum += 5
            if lineNum >= len(data):
                break
            showMore = raw_input()
            if showMore != 'm':
                break
        summary = raw_input(Fore.GREEN + Style.BRIGHT +
                            'summary/focus (may leave blank): ' +
                            Style.RESET_ALL) or None
    if summary: summary = summary.strip()

    paragraphs = []
    lineNum = len(data) - 1
    try:
        while not re.match(r'outquote(\(s\))?s?:', data[lineNum].lower()) \
            and data[lineNum].lower().find('word count:') < 0 \
            and data[lineNum].lower().find('focus sentence:') < 0:
            paragraphs = [data[lineNum].strip()] + paragraphs
            lineNum -= 1
        paragraphs = filter(None, paragraphs)  # removes empty strings
    except IndexError:  # no focus sentence or outquote ever reached
        print(Fore.RED + content)
        print(
            Back.RED + Fore.WHITE +
            'No focus sentence or outquote; content could not be isolated. Article skipped.'
            + Back.RESET + Fore.RED)
        return title
    paragraphs = raw_input((Fore.GREEN + Style.BRIGHT + 'content: ' +
                         Style.RESET_ALL + '({0} ... {1}) ').format(
                         paragraphs[0], paragraphs[-1])).split('\n') or paragraphs

    return True


def cleanName(name):
    name = name.replace(' - ', '-')
    # remove nickname formatting e.g. "By Ying Zi (Jessy) Mei"
    nicknameRegex = re.compile(r"\([\w\s-]*\)\s")
    name = nicknameRegex.sub('', name)  # removes nicknames
    return name


def main():
    print(
        "This utility will walk you through the uploading of all articles in the current Issue."
    )
    print("Press ^C at any time to quit.\n")
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    drive_service = discovery.build('drive', 'v3', http=http)

    # Gets all folder names under SBC
    page_token = None
    response = drive_service.files().list(
        q=
        "(mimeType='application/vnd.google-apps.folder' or mimeType='application/vnd.google-apps.document') and not trashed",
        spaces='drive',
        fields='nextPageToken, files(id, name, parents, mimeType)',
        pageToken=page_token).execute()
    files = response.get('files', [])  # if no key 'files', defaults to []
    SBC = next((file for file in files if file['name'] == 'SBC'), None)
    folders = getFoldersInFile(files, SBC['id'])

    unprocessedFiles = []
    for file in files:
        if file['mimeType'] == 'application/vnd.google-apps.document' and file.get(
                'parents', [None])[0] in folders:

            # find sectionName by getting folder with parentId
            sectionName = folders[file.get('parents', [None])[0]].upper()

            # create new download request
            request = drive_service.files().export_media(
                fileId=file['id'], mimeType='text/plain')
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(Fore.CYAN + Style.BRIGHT + sectionName, end='')
                print(
                    Fore.BLUE + ' ' + file['name'] + Style.RESET_ALL, end=' ')
                print('%d%%' % int(status.progress() * 100))

            if 'worldbeat' in file['name'].lower():
                print(Fore.RED + Style.BRIGHT + 'Worldbeat skipped.' + Style.RESET_ALL)
                continue

            status = readArticle(fh.getvalue(), file['name'])
            if type(status) is str: unprocessedFiles.append(file['name'])
            print('\n')

    if len(unprocessedFiles) > 0:
        print(Back.RED + Fore.WHITE + 'The title of unprocessed files: ' +
              Back.RESET + Fore.RED)
        print(*unprocessedFiles, sep='\n')
    page_token = response.get('nextPageToken', None)
    if page_token is None:
        return


def getFoldersInFile(files, parentFolderId):
    folders = {}
    for file in files:
        # check if parent folder is SBC and file type is folder
        if file.get('parents', [None])[0] == parentFolderId and file.get(
                'mimeType') == 'application/vnd.google-apps.folder':
            folders[file['id']] = file['name']
    return folders


if __name__ == '__main__':
    if args.read_article:
        with open(args.read_article) as file:
            readArticle(file.read())
    else:
        main()
