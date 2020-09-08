#!/usr/bin/python3
# -*- coding: utf-8 -*-
#%# family=contrib
#%# capabilities=autoconf
'''
=head1 NAME
nvme

=head1 DESCRIPTION
Shows info about installed nvme disks.

=head1 VERSION
0.0.1

=head1 COPYRIGHT
GPL VERSION 3
'''
import subprocess
import shutil
import json
import sys
import re


MODE_AUTOCONF = len(sys.argv) > 1 and sys.argv[1] == 'autoconf'
MODE_CONFIG = len(sys.argv) > 1 and sys.argv[1] == 'config'


def nvme_run(*args, append_json_flag=True) -> dict:
    """ Invokes the nvme-cli command. """
    call_options = ['nvme', *args]
    # This is needed because vendor extensions can use different
    # flag for json output (e.g. --json for Intel):
    if append_json_flag:
        call_options.append('--output-format=json')
    result = subprocess.run(call_options,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    return json.loads(result.stdout.decode('utf-8'))


def nvme_get_devices() -> list:
    """ Helper: returns device list. """
    return nvme_run('list').get('Devices', [])


def ktoc(degrees) -> int:
    """ Converts Kelvins into Celsius. """
    return degrees - 273


def clean_fieldname(text: str) -> str:
    """ Sanitizes input and yields safe ascii strings. """
    if text == 'root':
        return '_root'
    return re.sub(r"(^[^A-Za-z_]|[^A-Za-z0-9_])", "_", text)


def print_data(config: dict, values: dict, **kwargs) -> str:
    """ This function displays either config, or values for current multigraph. """
    print_data = config if MODE_CONFIG else values
    rendered_text = ""

    if 'multigraph' in kwargs:
        print_data = {'multigraph': kwargs['multigraph'], **print_data}

    for key, value in print_data.items():
        rendered_text += f"{key} {value}\n"

    return rendered_text.lstrip()


def graph_temperatures(devices: dict) -> str:
    """ This function displays the drives' temperature. """
    values = {}
    config = dict(
        graph_title='NVMe disks temperatures',
        graph_category='sensors',
        graph_info='The graph shows nvme disks temperature.',
        graph_args='--base 1000',
        graph_vlabel='Celsius')

    for key, info in devices.items():
        values[f'{key}.value'] = ktoc(info['metrics']['temperature'])
        config[f'{key}.label'] = info['system_name']

        warn_temp = info['id_ctrl']['wctemp']
        if warn_temp > 0:
            config[f'{key}.warning'] = ':{}'.format(ktoc(warn_temp))
        else:
            config[f'{key}.warning'] = ':70'

        crit_temp = info['id_ctrl']['cctemp']
        if crit_temp > 0:
            config[f'{key}.critical'] = ':{}'.format(ktoc(crit_temp))
        else:
            config[f'{key}.critical'] = ':85'

    return print_data(config, values, multigraph='nvme_temp')


def graph_throttle_info(devices: dict) -> str:
    """ This function displays the drives' throttle event count. """
    values = {}
    config = dict(
        graph_title='NVMe disks throttling',
        graph_category='disk',
        graph_info='The graph shows nvme disks throttling event count.',
        graph_args='--base 1000 --lower-limit 0',
        graph_vlabel='Thermal throttle events')

    for key, info in devices.items():
        values[f'{key}.value'] = info['metrics']['thm_temp1_trans_count']
        config[f'{key}.label'] = info['system_name']
        config[f'{key}.type'] = 'DERIVE'
        config[f'{key}.min'] = 0

    return print_data(config, values, multigraph='nvme_throtlling')


def graph_wearout(devices: dict) -> str:
    """ This function displays the drives' percent_used metric. """
    values = {}
    config = dict(
        graph_title='NVMe disks wearout',
        graph_category='disk',
        graph_info='The graph shows nvme disks wearout (percentage_used)',
        graph_args='--base 1000 --lower-limit 0 --upper-limit 105',
        graph_vlabel='%')

    for key, info in devices.items():
        config[f'{key}.label'] = info['system_name']
        config[f'{key}.critical'] = ':95'
        values[f'{key}.value'] = info['metrics']['percent_used']

    return print_data(config, values, multigraph='nvme_wearout')


def graph_error_rate(devices: dict) -> str:
    """ This function displays the drives' media_errors metric. """
    values = {}
    config = dict(
        graph_title='NVMe media errors',
        graph_category='disk',
        graph_info='The graph shows nvme disks errors (media_errors)',
        graph_args='--base 1000',
        graph_vlabel='media_errors')

    for key, info in devices.items():
        values[f'{key}.value'] = info['metrics']['media_errors']
        config[f'{key}.label'] = info['system_name']
        config[f'{key}.type'] = 'DERIVE'
        config[f'{key}.min'] = 0
        config[f'{key}.info'] = ("Indicates the number of unrecovered data integrity "
            "errors detected by the controller. Errors such as uncorrectable ECC, CRC "
            "checksum failure, or LBA tag mismatch are included in this field.")

    return print_data(config, values, multigraph='nvme_errors')


def graph_spare(devices: dict) -> str:
    """ This function displays the drives' available_spare metric. """
    values = {}
    config = dict(
        graph_title='NVMe health',
        graph_category='disk',
        graph_info='The graph shows nvme disks available spare blocks.',
        graph_args='--base 1000 --lower-limit 0 --upper-limit 105',
        graph_vlabel='Spare space left, %')

    for key, info in devices.items():
        config[f'{key}.label'] = info['system_name']
        config[f'{key}.critical'] = "{}:".format(info['metrics']['spare_thresh'])
        values[f'{key}.value'] = info['metrics']['avail_spare']

    return print_data(config, values, multigraph='nvme_available_spare')


def get_devices() -> dict:
    """ Returns nvme device list. """
    devices = {}
    for device in nvme_get_devices():
        device_path = device['DevicePath']
        device_metrics = nvme_run('smart-log', device_path)
        device_controller = nvme_run('id-ctrl', device_path)
        munin_key = clean_fieldname(device_path)

        devices[munin_key] = dict(
            device_path=device_path,
            system_name=device_path.replace('/dev/', ''),
            name=device['ModelNumber'],
            serial=device['SerialNumber'],
            metrics=device_metrics,
            id_ctrl=device_controller)

    return devices


if MODE_AUTOCONF:
    if shutil.which('nvme') is not None:
        if len(nvme_get_devices()) > 0:
            print('yes')
        else:
            print('no (no nvme devices found)')
    else:
        print('no (cannot find nvme-cli binary)')
    sys.exit(0)
else:
    # All local functions with names starting with "graph_" are autoloaded
    # and executed on "fetch" or "config" call:
    autoloaded_graphs = [ graph
        for name, graph in locals().items()
        if callable(graph) and name.startswith('graph_') ]

    devices = get_devices()

    for graph_callback in autoloaded_graphs:
        print(graph_callback(devices))
