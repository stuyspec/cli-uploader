from colorama import Fore, Back, Style
import re

def represents_int(s):
    s = s.strip()
    try:
        int(s)
        return True
    except ValueError:
        return False


def identify_line_manually(lines, missing_value):
    """Takes list of paragraphs and returns user input for the line # of any
    missing_value."""
    print(Fore.RED + Style.BRIGHT + missing_value.upper() +
          ' could not be found. Press ENTER to extend ' +
          'article. Input a line # to indicate ' + missing_value.upper() +
          ', "n" to indicate nonexistence.' + Style.RESET_ALL)
    line_num = 0
    while line_num + 5 < len(lines):
        if line_num > 0 and line_num % 5 == 0:
            user_option = raw_input()
            if represents_int(user_option):
                return int(user_option)
            elif user_option != '':
                break
        print('[{}] {}'.format(line_num, lines[line_num]))
        line_num += 1

    print('\n[**INITIAL SCANNING FAILED**]\n')
    line_num = 0
    for line_num in range(len(lines)):
        print('[{}] {}'.format(line_num, lines[line_num]))
    while 1:
        user_option = raw_input()
        if represents_int(user_option):
            return int(user_option)
        elif user_option != '':
            break
    return -1


def get_title(line):
    line = re.sub(r'Title:\s+', '', line.strip())
    if re.search(r'The Spectator\s?\/[^\/]*\/\s?Issue\s?\d\d?', line):
        while 1:
            title = raw_input(Fore.RED + Style.BRIGHT + 'title COULD NOT be found: ')
            if title != '':
                return title
    print(Fore.GREEN + Style.BRIGHT + 'title: ' + Style.RESET_ALL +
          '({}) '.format(line))
    return line


def clean_name(name):
    name = name.replace(' - ', '-')
    # remove nickname formatting e.g. "By Ying Zi (Jessy) Mei"
    name = re.sub(r"\([\w\s-]*\)\s", '', name)
    return name


def get_contributors(byline):
    byline = re.sub(r"By:?", '', byline).strip()
    byline = re.findall(r"[\w\p{L}\p{M}']+|[.,!-?;]", byline)

    contributors = []
    cutoff = 0
    for i in range(0, len(byline)):
        if byline[i] in ',&' or byline[i] == 'and':
            name = clean_name(' '.join(byline[cutoff:i]))
            contributors.append(name)
            cutoff = i + 1
    contributors.append(clean_name(' '.join(
        byline[cutoff:])))  # add last contributor
    contributors = filter(None, contributors)  # removes empty strings
    print((Fore.GREEN + Style.BRIGHT + 'contributors : ' + Style.RESET_ALL +
           '({0}) ').format(', '.join(contributors)))
    return contributors


HEADER_LINE_PATTERN = re.compile(
    r'Request:|Article:|(?i)(outquote(\(s\))?s?:)|(focus\s+sentence:)|(word(s)?:?\s\d{2,4})|(\d{2,4}\swords)|(word count:?\s?\d{2,4})'
)


def get_content_start(lines):
    try:
        header_end = next((index
                           for index, value in enumerate(reversed(lines))
                           if HEADER_LINE_PATTERN.search(value)))
        return len(lines) - header_end
    except StopIteration:
        return -1


def get_summary(line):
    line = re.sub(r"(?i)Focus Sentence:?", '', line).strip()
    print(Fore.GREEN + Style.BRIGHT + 'summary/focus: ' + Style.RESET_ALL +
          '({0}) ').format(line)
    return line