#!/usr/bin/env python3

from cmath import inf
from sys import argv, exit, stderr, stdout
from os import path, system
from yaml import safe_load
import functools
import json
import requests


##################    MAPPINGS    #####################


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


####################    UTILS    ####################


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


def replace_all(target: str, replaces: dict[str, str]) -> str:
    for rep in replaces:
        if replaces[rep] == None:
            raise ValueError("Missing value for %s" % rep)
        target = target.replace(rep, replaces[rep])
    return target


################## LOG FUNCTIONS ##################


def log_error(message: str):
    stderr.write('%s[Error]   %s%s\n' % (bcolors.FAIL, bcolors.ENDC, message))


def log_success(message: str):
    print('%s[Success] %s%s' % (bcolors.OKGREEN, bcolors.ENDC, message))


def log_info(message: str):
    print('%s[Info]    %s%s' % (bcolors.HEADER, bcolors.ENDC, message))


def log_header(message: str):
    line = ("%s%s%s" % (bcolors.UNDERLINE, message, bcolors.ENDC)).center(60, ' ')
    print("".center(50, '-'))
    print("%s\n" % line)


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


# def generate_environment(selected: dict[str, str], env: dict[str, str]) -> str:
#         return "\n".join([key.upper().replace('-', '_') + '\t= ' + env[key] for key in selected]) + "\n"


def rule_to_text(rule: str, body: dict[str, str], env: dict[str, str]) -> str:
    result = "%s:\t%s\n" % (
        rule,
        " ".join(body['prerules'])
    ) if 'prerules' in body.keys() else "%s:\n" % (rule)
    if 'command' in body.keys():
        result += "\t@%s%s\n" % (
            " ".join(
                [key.upper().replace('-', '_') + '=' + '$(' + key.upper().replace('-', '_') + ')' for key in env.keys()]
            ) + " " if env and 'use_environment' in body.keys() and body['use_environment'] else "",
            body['command']
        )
    return result


def json_to_makefile(obj: dict[str, any]) -> str:
    result = "# This is an automatically generated Makefile, do not modify!\n"
    result += "# Edit your lagen configuration to regenerate it.\n\n"
    if obj['environment']:
        result += "\n".join([key + '\t= ' + obj['environment'][key] for key in obj['environment'].keys()]) + "\n\n\n"
    result += "\n".join(
        [rule_to_text(rule, obj['rules'][rule], obj['environment']) for rule in obj['rules']]
    )
    phonies = list()
    for rule in obj['rules']:
        if 'phony' not in obj['rules'][rule].keys() or obj['rules'][rule]['phony']:
            phonies.append(rule)

    result += "\n.PHONY:\t%s" % (' \\\n\t\t'.join(phonies))
    return result



###############    FILE GENERATION    ################


# def download_file(url: str) -> bytes:
#     buffer = bytes()
#     response = requests.get(url, stream=True)
#     total_length = response.headers.get('content-length')

#     if (response.status_code != 200):
#         raise ValueError('Response status_code : %d, expected %d' % (response.status_code, 200))
#     if total_length is None:
#         buffer += response.content
#     else:
#         dl = 0
#         total_length = int(total_length)
#         for data in response.iter_content(chunk_size=4096):
#             dl += len(data)
#             buffer += data

#             done = int(50 * dl / total_length)
#             stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50-done)))
#             stdout.flush()
#     stdout.write("\n")
#     return buffer


def generate_makefile(entry: dict[str, any], env: dict[str, str], type: str):
    makefile = {
        'rules': {
            'all': {
                'prerules': ['install']
            },
            'apply': {
                'command': 'terraform apply',
                'use_environment': True
            },
            'build': {
                'command': get_build_command(entry=entry),
            },
            'deploy': {
                'prerules': ['build', 'deploy'],
            },
            'init': {
                'command': 'terraform init',
            },
            'install': {
                'command': get_install_command(entry=entry),
            },
            'plan': {
                'command': 'terraform plan',
                'use_environment': True
            }
        },
        'environment': {},
    }

    if 'environment' in entry.keys():
        try:
            for key in entry['environment']:
                makefile['environment'].update({ key.upper().replace('-', '_'): env[key] })
        except KeyError as e:
            raise Exception('Environment key %s not in global environment' % str(e))

    if 'rules' in entry.keys():
        for rule in entry['rules']:
            makefile['rules'][rule['name']] = rule
            del makefile['rules'][rule['name']]['name']

    if 'scripts' in entry.keys():
        for script in entry['scripts']:
            print(script)
            makefile['rules'][script] = {
                'command': '%s run %s' % (entry['package_manager'], script)
            }

    try:
        log_info('Generating Makefile...')
        with open(path.join(entry['name'], 'Makefile'), 'w' if path.exists(path.join(entry['name'], 'Makefile')) else 'x') as f:
            f.write(json_to_makefile(obj=makefile))
    except (OSError, IOError):
        raise Exception('Unable to generate Makefile (%s)' % (str(e)))


def generate_package_json(entry: dict[str, str], config: any):
    package = {
        "name": entry["name"],
        "author": config["author"] if 'author' in config.keys() else "",
        "version": entry["version"] if 'version' in entry.keys() else "0.0.0-development",
        "main": entry["main"] if 'main' in entry.keys() else "index.js",
        "scripts": {
            "build": entry['build'] if 'build' in entry.keys() else "echo \"No build command specified, using Terraform default zip\""
        },
        "dependencies": entry['dependencies'] if 'dependencies' in entry.keys() else {},
        "devDependencies": entry['devDependencies'] if 'devDependencies' in entry.keys() else {},
    }

    if 'scripts' in entry.keys():
        package['scripts'].update(entry['scripts'])
    if type == 'global':
        package['devDependencies'].update({ '@lucas-cox/lagen': 'latest' })

    try:
        log_info('Generating package.json...')
        with open(path.join(entry['name'], 'package.json'), 'w' if path.exists(path.join(entry['name'], 'package.json')) else 'x') as f:
            json.dump(package, fp=f, indent=4)

    except (OSError, IOError) as e:
        raise Exception('Unable to edit package.json (%s)' % (str(e)))


##################    GENERATORS    ########################


def generate_node_lambda(entry: dict[str, str], config: any):
    if not 'package_manager' in entry.keys():
        entry['package_manager'] = 'npm'
    if entry['package_manager'] != 'npm' and entry['package_manager'] != 'yarn':
        raise ValueError('Invalid value for node package manager: %s, available are %s' % (
            entry['package_manager'],
            str(entries[entry['type']]['package_managers'])
        ))
    log_info('Creating ')
    system("mkdir -p %s" % path.join(config['cwd'], entry['name']))
    generate_makefile(entry=entry, env=config['environment'], type=config['type'])
    # generate_terraform
    generate_package_json(entry=entry, config=config)
    # create source directory and entry_point


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
            log_success('Entry successfully generated !\n')
    except KeyError as e:
        log_error('Unknown entry type: %s.' % (entry['type']))
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
