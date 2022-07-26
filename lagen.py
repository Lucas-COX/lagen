#!/usr/bin/env python3

from sys import argv, exit
from os import path, system
from yaml import safe_load
import threading


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


################    FILE GENERATORS    #####################


def generate_makefile(dir: str, env: any, type: str):
    with open(path.join(dir, 'Makefile'), 'x') as m:
        m.write("Yuhooo")



##################    GENERATORS    ########################


def generate_node_lambda(entry: any, config: any):
    # try:
        print(entry)
        system("mkdir -p %s" % path.join(config['cwd'], entry['name']))
        generate_makefile(dir=entry['name'], env=config['environment'], type=config['type'])

    # except Exception:
    #     print('Could not generate node lambda')
    #     exit(1)


def generate_go_lambda(entry: any, config: any):
    pass


#################     MAIN ALGORITHM     #################


def generate_entries(config: any) -> None:
    threads = list()
    mappings = {
        'go': generate_go_lambda,
        'node': generate_node_lambda,
    }
    print(config)
    try:
        for entry in config['entries']:
            threads.append(threading.Thread(target=mappings[entry['type']], args=(entry, config)))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    except KeyError:
        print('Unknown entry type: %s' % entry['type'])
        exit(1)



def main():
    if len(argv) > 2:
        exit_usage()
    config = parse_config('.' if len(argv) == 1 else argv[1])
    config['cwd'] = '.' if len(argv) == 1 else argv[1]
    generate_entries(config)



if __name__ == '__main__':
    main()