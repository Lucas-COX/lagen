#!/usr/bin/env python3

from cmath import inf
from sys import argv, exit, stderr, stdout
from os import path, system
from yaml import safe_load
import functools
import requests


################    UTILS    #####################


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

entries = {
    'node': {
        'install_command': '{{ pm }} install',
        'build_command': '{{ pm }} run build',
        'package_managers': ['npm', 'yarn'],
    },
    'go': {
        'install_command': 'go mod tidy',
        'build_command': 'go build {{ name }}',
    }
}


def exit_usage():
    print('USAGE:   lagen [path_to_project]')


def parse_config(dir: str) -> dict:
    try:
        with open(path.join(dir, '.lagen/main.yml')) as file:
            content = safe_load(file)
            return content
    except:
        print('Bad configuration file: %s' % (path.join(dir, '.lagen/main.yml')))
        exit(1)


def log_error(message: str):
    stderr.write('%s[Error]%s%s\n' % (bcolors.FAIL, bcolors.ENDC, message))


def log_success(message: str):
    print('%s[Success]%s%s' % (bcolors.OKGREEN, bcolors.ENDC, message))


def log_info(message: str):
    print('%s[Info]%s%s' % (bcolors.HEADER, bcolors.ENDC, message))


def log_header(message: str):
    line = ("%s%s%s" % (bcolors.UNDERLINE, message, bcolors.ENDC)).center(75, ' ')
    print("\n%s\n" % line)


def replace_all(target: str, replaces: dict[str, str]) -> str:
    for rep in replaces:
        if replaces[rep] == None:
            raise ValueError("Missing value for %s" % rep)
        target = target.replace(rep, replaces[rep])
    return target


################     TEXT GENERATION     ###################


def get_build_command(entry: dict[str, str]) -> str:
    replacements = {
        '{{ pm }}': entry['package_manager'],
        '{{ name }}': entry['name']
    }
    return replace_all(entries[entry['type']]['build_command'], replacements)


def get_install_command(entry: dict[str, str]) -> str:
    replacements = {
        '{{ pm }}': entry['package_manager'],
    }
    return replace_all(entries[entry['type']]['install_command'], replacements)


def generate_environment(selected: dict[str, str], env: dict[str, str]) -> str:
        return "\n".join([key.upper().replace('-', '_') + '\t= ' + env[key] for key in selected]) + "\n"


############### FILE GENERATION ################


def download_file(url: str) -> bytes:
    buffer = bytes()
    response = requests.get(url, stream=True)
    total_length = response.headers.get('content-length')

    if (response.status_code != 200):
        raise ValueError('Response status_code : %d, expected %d' % (response.status_code, 200))
    if total_length is None:
        buffer += response.content
    else:
        dl = 0
        total_length = int(total_length)
        for data in response.iter_content(chunk_size=4096):
            dl += len(data)
            buffer += data

            done = int(50 * dl / total_length)
            stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50-done)))
            stdout.flush()
    stdout.write("\n")
    return buffer


def generate_makefile(entry: dict[str, str], env: dict[str, str], type: str):
    urls = {
        'lambdas': 'https://raw.githubusercontent.com/Lucas-COX/lagen/master/templates/lambdas/Makefile'
    }
    replacements = {
        '{{ env }}': functools.reduce(
            lambda x, y: x + y,
            [key.upper().replace('-', '_') + '=' + '$(' + key.upper().replace('-', '_') + ') ' for key in entry['environment']]
        ) if 'environment' in entry.keys() else "",
        '{{ build_command }}': get_build_command(entry=entry),
        '{{ install_command }}': get_install_command(entry=entry),
    }
    try:
        replacements['{{ global_env }}'] = generate_environment(entry['environment'], env) + '\n\n' if 'environment' in entry.keys() else ""
    except KeyError as e:
        raise Exception('Environment key %s is not in global environment' % (str(e)))

    try:
        log_info("[%s] Downloading Makefile from template..." % entry['name'])
        file = download_file(urls[type]).decode('utf-8')
        log_success('[%s] Makefile template downloaded.' % entry['name'])
    except ValueError as e:
        raise Exception('An error occured while downloading Makefile template (%s)' % str(e))
    except KeyError:
        raise Exception('Unknown type : %s' % type)

    log_info('[%s] Editing Makefile...' % entry['name'])

    file = replace_all(file, replacements)

    try:
        f = open(path.join(entry['name'], 'Makefile'), 'w' if path.exists(path.join(entry['name'], 'Makefile')) else 'x')
        f.write(file)
    except (OSError, IOError) as e:
        raise Exception('Unable to edit Makefile (%s)' % (str(e)))



##################    GENERATORS    ########################


def generate_node_lambda(entry: dict[str, str], config: any):
    if not 'package_manager' in entry.keys():
        entry['package_manager'] = 'npm'
    if entry['package_manager'] != 'npm' and entry['package_manager'] != 'yarn':
        raise ValueError('Invalid value for node package manager: %s, available are %s' % (
            entry['package_manager'],
            str(entries[entry['type']]['package_managers'])
        ))
    system("mkdir -p %s" % path.join(config['cwd'], entry['name']))
    generate_makefile(entry=entry, env=config['environment'], type=config['type'])
    # generate_terraform
    # generate_package.json
    # create entry_point


def generate_go_lambda(entry: any, config: any):
    pass


#################     MAIN ALGORITHM     #################


def generate_entries(config: any) -> None:
    mappings = {
        'go': generate_go_lambda,
        'node': generate_node_lambda,
    }

    try:
        for entry in config['entries']:
            log_header("%s" % entry['name'].upper())
            mappings[entry['type']](entry, config)
            log_success('[%s] Entry successfully generated !\n' % entry['name'])
    except KeyError as e:
        log_error('[%s] Unknown entry type: %s.' % (entry['name'], entry['type']))
        print(e)
        exit(1)
    # except Exception as e:
    #     log_error('[%s] %s' % (entry['name'], str(e)))
    #     exit(1)


def main():
    if len(argv) > 2:
        exit_usage()
    config = parse_config('.' if len(argv) == 1 else argv[1])
    config['cwd'] = '.' if len(argv) == 1 else argv[1]
    generate_entries(config)


if __name__ == '__main__':
    main()
