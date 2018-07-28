# docker-dup
Run multiple instances of a set of Docker containers on different networks via docker-compose.

## Requirements
- Linux host
- Python 3.6+
- Python yaml module (`pip install yaml`)
- docker
- docker-compose

## Installation
`wget https://raw.githubusercontent.com/sears-s/docker-dup/master/docker-dup.py`

## Usage
```
usage: docker-dup.py [-h] command ...

docker-dup - Run multiple instances of a set of Docker containers on different
networks via docker-compose. Settings located in ./settings.yml, which is
created automatically if it does not exist.

positional arguments:
  command
    run       run .yml config file via docker-compose up
    runi      run an image as a single container
    ex        execute scripts for currently running containers
    stop      stop and remove all containers and networks
    clear     remove all images with --force
    mkc       create .yml config file template
    mki       create docker image template in image directory
    shell     get a shell to a running container

optional arguments:
  -h, --help  show this help message and exit
```