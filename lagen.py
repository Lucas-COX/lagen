#!/usr/bin/env python3

from dataclasses import replace
from sys import argv, exit, stderr, stdout
from os import path, system, remove
from yaml import safe_load
import functools
import threading
import requests


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


################    FILE GENERATORS    #####################


def download_file(url: str, filename: str) -> bytes:
    # with open(filename, "wb") as f:
        buffer = bytes()
        response = requests.get(url, stream=True)
        total_length = response.headers.get('content-length')

        if (response.status_code != 200):
           #  f.close()
            remove(filename)
            raise ValueError('Response status_code : %d, expected %d' % (response.status_code, 200))
        if total_length is None:  # no content length header
            # f.write(response.content)
            buffer += response.content
        else:
            dl = 0
            total_length = int(total_length)
            for data in response.iter_content(chunk_size=4096):
                dl += len(data)
               # f.write(data)
                buffer += data

                done = int(50 * dl / total_length)
                stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50-done)))
                stdout.flush()
        stdout.write("\n")
        return buffer


def replace_in_file(file: str, replaces: dict[str, str]) -> str:
    for rep in replaces:
        file = file.replace(rep, replaces[rep])
    return file


def generate_makefile(dir: str, env: dict[str, str], type: str):
    mappings = {
        'lambdas': 'https://raw.githubusercontent.com/Lucas-COX/lagen/master/templates/lambdas/Makefile'
    }
    replaces = {
        '{{ env }}': functools.reduce(
            lambda x, y: x + y,
            [key.upper().replace('-', '_') + '=' + '$(' + key.upper().replace('-', '_') + ') ' for key in env]
        ),
    }
    try:
        log_info("[%s] Downloading Makefile from template..." % dir)
        file = download_file(
            mappings[type],
            path.join(dir, 'Makefile')
        ).decode('utf-8')
        log_success('[%s] Makefile template downloaded.' % dir)
        log_info('[%s] Editing Makefile...' % dir)
        file = replace_in_file(file, replaces)
        f = open(path.join(dir, 'Makefile'), 'w' if path.exists(path.join(dir, 'Makefile')) else 'x')
        f.write(file)

    except KeyError:
        raise Exception('Unknown type : %s' % type)

    except ValueError as e:
        raise Exception('An error occured while downloading Makefile template : %s' % str(e))

    except (OSError, IOError) as e:
        raise Exception('Unable to edit Makefile : %s' % (str(e)))



##################    GENERATORS    ########################


def generate_node_lambda(entry: any, config: any):
    # try:
        system("mkdir -p %s" % path.join(config['cwd'], entry['name']))
        generate_makefile(dir=entry['name'], env=config['environment'], type=config['type'])
    # except Exception as e:
    #     log_error('[%s] An error occured while generating the entry :\n\n"%s"\n' % (entry['name'], str(e)))


def generate_go_lambda(entry: any, config: any):
    pass


#################     MAIN ALGORITHM     #################


def generate_entries(config: any) -> None:
    threads = list()
    mappings = {
        'go': generate_go_lambda,
        'node': generate_node_lambda,
    }
    try:
        # for entry in config['entries']:
        #     threads.append(threading.Thread(target=mappings[entry['type']], args=(entry, config)))
        # for thread in threads:
        #     thread.start()
        # for thread in threads:
        #     thread.join()
        for entry in config['entries']:
            mappings[entry['type']](entry, config)
    except KeyError:
        log_error('[%s] Unknown entry type.' % entry['type'])
        exit(1)
    except Exception as e:
        log_error('[%s] %s' % (entry['name'], str(e)))


def main():
    if len(argv) > 2:
        exit_usage()
    config = parse_config('.' if len(argv) == 1 else argv[1])
    config['cwd'] = '.' if len(argv) == 1 else argv[1]
    generate_entries(config)


if __name__ == '__main__':
    main()
