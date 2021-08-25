import sys
import os
import importlib
import yaml
import logging

BADGER_PLUGIN_ROOT = 'D:/Projects/Badger-Plugins'
sys.path.append(BADGER_PLUGIN_ROOT)


def scan_plugins(root):
    factory = {}
    for ptype in ['algorithm', 'interface', 'environment']:
        factory[ptype] = {}

        proot = os.path.join(root, f'{ptype}s')

        plugins = [fname for fname in os.listdir(proot)
                   if os.path.exists(os.path.join(proot, fname, '__init__.py'))]
        for pname in plugins:
            factory[ptype][pname] = None

    return factory


def load_plugin(root, pname, ptype):
    assert ptype in ['algorithm', 'interface',
                     'environment'], f'Invalid plugin type {ptype}'

    proot = os.path.join(root, f'{ptype}s')

    # Load the params in the configs
    configs = None
    with open(os.path.join(proot, pname, 'configs.yaml'), 'r') as f:
        try:
            configs = yaml.safe_load(f)
        except yaml.YAMLError:
            logging.error(
                f'Error loading plugin {ptype} {pname}: invalid config')
    if configs is None:
        params = None
    else:
        try:
            params = configs['params']
        except KeyError:
            params = None

    # Load module
    module = importlib.import_module(f'{ptype}s.{pname}')

    if ptype == 'algorithm':
        plugin = [module.optimize, params]
    elif ptype == 'interface':
        plugin = [module.Interface, params]
    elif ptype == 'environment':
        plugin = [module.Environment, params]

    BADGER_FACTORY[ptype][pname] = plugin

    return plugin


def get_plug(root, name, ptype):
    try:
        plug = BADGER_FACTORY[ptype][name]
        if plug is None:  # lazy loading
            plug = load_plugin(root, name, ptype)
            BADGER_FACTORY[ptype][name] = plug
    except KeyError:
        logging.error(
            f'Error loading plugin {ptype} {name}: plugin not found')
        plug = None

    return plug


def get_algo(name):
    return get_plug(BADGER_PLUGIN_ROOT, name, 'algorithm')


def get_intf(name):
    return get_plug(BADGER_PLUGIN_ROOT, name, 'interface')


def get_env(name):
    return get_plug(BADGER_PLUGIN_ROOT, name, 'environment')


BADGER_FACTORY = scan_plugins(BADGER_PLUGIN_ROOT)
