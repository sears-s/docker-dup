#!/usr/bin/python3

# imports
from argparse import ArgumentParser
from os.path import isfile
from subprocess import call

from yaml import dump, load

# constants
ext = '.yml'
settings_path = 'settings' + ext
compose_path = 'docker-compose' + ext

# create settings if it doesn't exist
if not isfile(settings_path):
    # create dict
    new_settings = {
        'version': '3.7',
        'image_dir': './',
        'variables': {
            'subnet': '10.0'
        },
        'services': None,
        'networks': None,
        'scripts': None
    }

    # write to the file
    with open(settings_path, 'w') as new_settings_file:
        dump(new_settings, new_settings_file, default_flow_style=False)


# run command function
def run(args):
    # get args
    if args.config_file.endswith(ext):
        config_path = args.config_file
    else:
        config_path = args.config_file + ext
    num = args.num

    # check if config file exists
    if not isfile(config_path):
        print(f'Error: config_file {config_path} does not exist.')
        exit(1)

    # check num
    if num < 1 or num > 99:
        print('Error: num must be 1-99.')
        exit(1)

    # load settings
    with open(settings_path, 'r') as settings_file:
        settings = load(settings_file)

    # load config file
    with open(config_path, 'r') as config_file:
        config = load(config_file)

    # combine services
    services = {}
    if settings['services']:
        services.update(settings['services'])
    if config['services']:
        services.update(config['services'])

    # combine scripts
    scripts = []
    if settings['scripts']:
        scripts.extend(settings['scripts'])
    if config['scripts']:
        scripts.extend(config['scripts'])

    # start compose dict
    compose = {
        'version': settings['version'],
        'services': {},
        'networks': {}
    }

    # start replacements dict
    reps = {
        'num': '',
        'num-l': '',
        'name': '',
        'name-n': ''
    }
    if settings['variables']:
        reps.update(settings['variables'])

    # iterate over services
    for name, service in services.items():

        # if service has codes
        if '%' in name:

            # get name and codes
            split = name.split('%')
            codes = split[0]
            new_name = reps['name'] = split[1]

            # parse codes and make service dicts
            first = others = {}
            if 'b' in codes:
                first = {
                    'build': settings['image_dir'] + new_name,
                    'image': new_name,
                    **service
                }
                if 'd' in codes:
                    others = {
                        'image': new_name,
                        'depends_on': [new_name + '-1'],
                        **service
                    }

            # iterate if d code
            if 'd' in codes:
                for i in range(1, num + 1):

                    # set replacements
                    reps['num'] = str(i)
                    reps['num-l'] = str(i).zfill(2)
                    reps['name-n'] = f'{new_name}-{str(i)}'

                    # if first instance and b code
                    if i == 1 and 'b' in codes:
                        compose['services'][reps['name-n']] = rep(first, reps)

                    # if other instances
                    else:
                        if 'b' in codes:
                            compose['services'][reps['name-n']] = rep(others, reps)
                        else:
                            compose['services'][reps['name-n']] = rep(service, reps)

            # if one instance
            else:
                compose['services'][new_name] = rep(first, reps)

        # if no codes
        else:
            reps['name'] = name
            compose['services'][name] = rep(service, reps)

    # iterate over networks
    if settings['networks']:
        for name, network in settings['networks'].items():

            # check if network has codes
            if '%' in name:

                # get name and codes
                split = name.split('%')
                codes = split[0]
                new_name = reps['name'] = split[1]

                # iterate if d code
                if 'd' in codes:
                    for i in range(1, num + 1):
                        # set replacements
                        reps['num'] = str(i)
                        reps['num-l'] = str(i).zfill(2)
                        reps['name-n'] = f'{new_name}-{str(i)}'

                        # add network
                        compose['networks'][reps['name-n']] = rep(network, reps)

            # no codes
            else:
                reps['name'] = name
                compose['networks'][name] = rep(network, reps)

    # write compose dict to file
    with open(compose_path, 'w') as compose_file:

        # write num as comment
        compose_file.write(f'#{num}\n')

        # write scripts as comments
        for script in scripts:
            compose_file.write(f'#{script}\n')

        # write yaml
        dump(compose, compose_file, default_flow_style=False)

    # remove previous instances
    if not args.restart:
        stop(None)

    # run compose
    command = 'DOCKER_CLIENT_TIMEOUT=600 COMPOSE_HTTP_TIMEOUT=600 docker-compose up'
    if args.build:
        command += ' --build'
    if args.detach:
        command += ' -d'
    call(command, shell=True)


# runi command function
def runi(args):
    # remove previous instances
    if not args.restart:
        stop(None)

    # build if option
    if args.build:
        call(f'docker build {args.image_name} -t {args.image_name}', shell=True)

    # run the image
    call(f'docker run {args.options} {args.image_name}', shell=True)


# stop command function
def stop(args):
    # stop all containers
    call('docker stop $(docker ps -a -q)', shell=True)

    # remove all containers
    call('docker rm $(docker ps -a -q)', shell=True)

    # remove unused networks
    call('docker network prune -f', shell=True)


# ex command function
def ex(args):
    # read compose file
    with open(compose_path, 'r') as compose_file:
        compose = compose_file.read()

    # get num
    num = int(compose.splitlines()[0][1])

    # load variables
    with open(settings_path, 'r') as settings_file:
        variables = load(settings_file)['variables']

    # start replacements dict
    reps = {
        'num': '',
        'num-l': ''
    }
    if variables:
        reps.update(variables)

    # get scripts
    scripts = []
    for line in compose.splitlines()[1:]:

        # if comment
        if line[0] == '#':

            # if code
            if '%' in line[1:]:

                # get script and codes
                split = line[1:].split('%')
                codes = split[0]
                script = split[1]

                # iterate if d code
                if 'd' in codes:
                    for i in range(1, num + 1):
                        # set replacements
                        reps['num'] = str(i)
                        reps['num-l'] = str(i).zfill(2)

                        # add script with replacements
                        scripts.append(rep(script, reps, False))

            # if no code
            else:
                scripts.append(line[1:])

        # stop after last comment
        else:
            break

    # run scripts
    for script in scripts:
        call(script, shell=True)


# clear command function
def clear(args):
    # remove all images
    call('docker rmi -f $(docker images -q -a)', shell=True)


# mkc command function
def mkc(args):
    # get args
    if args.config_file.endswith(ext):
        config_path = args.config_file
    else:
        config_path = args.config_file + ext

    # create config dict
    config = {
        'services': None,
        'scripts': None
    }

    # write the dict
    with open(config_path + ext, 'w') as config_file:
        dump(config, config_file, default_flow_style=False)


# mki command function
def mki(args):
    # get image directory from settings
    with open(settings_path, 'r') as settings_file:
        image_dir = load(settings_file)['image_dir']

    # make directory for image
    call(f'mkdir {image_dir}{args.image_name}', shell=True)

    # make blank Dockerfile
    call(f'touch {image_dir}{args.image_name}/Dockerfile', shell=True)


# shell command function
def shell(args):
    # get the shell
    call(f'docker exec -it {args.container_name} bash', shell=True)


# replacement function
def rep(i, reps, yaml=True):
    # convert dict to yaml string if yaml
    if yaml:
        s = dump(i, default_flow_style=False)
    else:
        s = i

    # do each replacement
    for key, value in reps.items():
        s = s.replace(f'_{key}_', value)

    # return as dict if yaml
    if yaml:
        return load(s)
    else:
        return s


# base parser
parser = ArgumentParser(
    description='docker-dup - '
                'Run multiple instances of a set of Docker containers on different networks via docker-compose. '
                f'Settings located in ./{settings_path}, which is created automatically if it does not exist.')
subparsers = parser.add_subparsers(metavar='command', dest='command')
subparsers.required = True

# run subparser
parser_run = subparsers.add_parser('run', help=f'run {ext} config file via docker-compose up')
parser_run.add_argument('config_file', help=f'path to {ext} file with or without the extension')
parser_run.add_argument('num', help='number of instances to create (1-99)', type=int)
parser_run.add_argument('-b', '--build', action='store_true', help='build images before running')
parser_run.add_argument('-d', '--detach', action='store_true', help='run in background')
parser_run.add_argument('-r', '--restart', action='store_true',
                        help='do not stop and remove all containers and networks before running')
parser_run.set_defaults(func=run)

# runi subparser
parser_runi = subparsers.add_parser('runi', help='run an image as a single container')
parser_runi.add_argument('image_name', help='path of directory image Dockerfile')
parser_runi.add_argument('-o', '--options', help='optional arguments to pass to docker run', type=str, default='')
parser_runi.add_argument('-b', '--build', action='store_true', help='build image before running')
parser_runi.add_argument('-r', '--restart', action='store_true',
                         help='do not stop and remove all containers and networks before running')
parser_runi.set_defaults(func=runi)

# script subparser
parser_ex = subparsers.add_parser('ex', help='execute scripts for currently running containers')
parser_ex.set_defaults(func=ex)

# stop subparser
parser_stop = subparsers.add_parser('stop', help='stop and remove all containers and networks')
parser_stop.set_defaults(func=stop)

# clear subparser
parser_clear = subparsers.add_parser('clear', help='remove all images with --force')
parser_clear.set_defaults(func=clear)

# mkc subparser
parser_mkc = subparsers.add_parser('mkc', help=f'create {ext} config file template')
parser_mkc.add_argument('config_file', help=f'path to {ext} file with or without the extension')
parser_mkc.set_defaults(func=mkc)

# mki subparser
parser_mki = subparsers.add_parser('mki', help='create docker image template in image directory')
parser_mki.add_argument('image_name', help='name of folder to create the image in')

# shell subparser
parser_shell = subparsers.add_parser('shell', help='get a shell to a running container')
parser_shell.add_argument('container_name', help='name of container, append -# if multiple instances')
parser_shell.set_defaults(func=shell)

# call respective function on args
arguments = parser.parse_args()
arguments.func(arguments)
