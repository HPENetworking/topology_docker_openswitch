# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
Custom Topology Docker Node for OpenSwitch.

    http://openswitch.net/
"""

from __future__ import unicode_literals, absolute_import
from __future__ import print_function, division

from json import loads
from subprocess import check_call

from topology_docker.node import DockerNode
from topology_docker.shell import DockerBashShell

from .shell import OpenSwitchVtyshShell


SETUP_SCRIPT = """\
import logging
from sys import argv
from time import sleep
from os.path import exists, split
from json import dumps, loads
from shlex import split as shsplit
from subprocess import check_call, check_output
from socket import AF_UNIX, SOCK_STREAM, socket, gethostname

import yaml

config_timeout = 300
swns_netns = '/var/run/netns/swns'
hwdesc_dir = '/etc/openswitch/hwdesc'
db_sock = '/var/run/openvswitch/db.sock'
switchd_pid = '/var/run/openvswitch/ops-switchd.pid'
query = {
    'method': 'transact',
    'params': [
        'OpenSwitch',
        {
            'op': 'select',
            'table': 'System',
            'where': [],
            'columns': ['cur_hw']
        }
    ],
    'id': id(db_sock)
}
sock = None


def create_interfaces():
    # Read ports from hardware description
    with open('{}/ports.yaml'.format(hwdesc_dir), 'r') as fd:
        ports_hwdesc = yaml.load(fd)
    hwports = [str(p['name']) for p in ports_hwdesc['ports']]

    # Get list of already created ports
    not_in_swns = check_output(shsplit(
        'ls /sys/class/net/'
    )).split()
    in_swns = check_output(shsplit(
        'ip netns exec swns ls /sys/class/net/'
    )).split()

    create_cmd_tpl = 'ip tuntap add dev {hwport} mode tap'
    netns_cmd_tpl = 'ip link set {hwport} netns swns'
    rename_int = 'ip link set {portlbl} name {hwport}'

    # Save port mapping information
    mapping_ports = {}

    # Map the port with the labels
    for portlbl in not_in_swns:
        if portlbl in ['lo', 'oobm', 'bonding_masters']:
            continue
        hwport = hwports.pop(0)
        mapping_ports[portlbl] = hwport
        logging.info(
            '  - Port {portlbl} moved to swns netns as {hwport}.'.format(
                **locals()
            )
        )
        try:
            check_call(shsplit(rename_int.format(**locals())))
            check_call(shsplit(netns_cmd_tpl.format(hwport=hwport)))
        except:
            raise Exception('Failed to map ports with port labels')

    # Writting mapping to file
    shared_dir_tmp = split(__file__)[0]
    with open('{}/port_mapping.json'.format(shared_dir_tmp), 'w') as json_file:
        json_file.write(dumps(mapping_ports))

    for hwport in hwports:
        if hwport in in_swns:
            logging.info('  - Port {} already present.'.format(hwport))
            continue

        logging.info('  - Port {} created.'.format(hwport))
        try:
            check_call(shsplit(create_cmd_tpl.format(hwport=hwport)))
        except:
            raise Exception('Failed to create tuntap')

        try:
            check_call(shsplit(netns_cmd_tpl.format(hwport=hwport)))
        except:
            raise Exception('Failed to move port to swns netns')
    check_call(shsplit('touch /tmp/ops-virt-ports-ready'))
    logging.info('  - Ports readiness notified to the image')

def cur_cfg_is_set():
    global sock
    if sock is None:
        sock = socket(AF_UNIX, SOCK_STREAM)
        sock.connect(db_sock)
    sock.send(dumps(query))
    response = loads(sock.recv(4096))
    try:
        return response['result'][0]['rows'][0]['cur_hw'] == 1
    except IndexError:
        return 0

def main():

    if '-d' in argv:
        logging.basicConfig(level=logging.DEBUG)

    logging.info('Waiting for swns netns...')
    for i in range(0, config_timeout):
        if not exists(swns_netns):
            sleep(0.1)
        else:
            break
    else:
        raise Exception('Timed out while waiting for swns.')

    logging.info('Waiting for hwdesc directory...')
    for i in range(0, config_timeout):
        if not exists(hwdesc_dir):
            sleep(0.1)
        else:
            break
    else:
        raise Exception('Timed out while waiting for hwdesc directory.')

    logging.info('Creating interfaces...')
    create_interfaces()

    logging.info('Waiting for DB socket...')
    for i in range(0, config_timeout):
        if not exists(db_sock):
            sleep(0.1)
        else:
            break
    else:
        raise Exception('Timed out while waiting for DB socket.')

    logging.info('Waiting for switchd pid...')
    for i in range(0, config_timeout):
        if not exists(switchd_pid):
            sleep(0.1)
        else:
            break
    else:
        raise Exception('Timed out while waiting for switchd pid.')

    logging.info('Wait for final hostname...')
    for i in range(0, config_timeout):
        if gethostname() != 'switch':
            sleep(0.1)
        else:
            break
    else:
        raise Exception('Timed out while waiting for final hostname.')

    logging.info('Waiting for cur_cfg...')
    for i in range(0, config_timeout):
        if not cur_cfg_is_set():
            sleep(0.1)
        else:
            break
    else:
        raise Exception('Timed out while waiting for cur_cfg.')

if __name__ == '__main__':
    main()
"""


PROCESS_LOG = """
#!/bin/bash
ovs-vsctl list Daemon >> /tmp/logs
echo "Coredump -->" >> /tmp/logs
coredumpctl gdb >> /tmp/logs
echo "All the running processes:" >> /tmp/logs
ps -aef >> /tmp/logs

systemctl status >> /tmp/systemctl
systemctl --state=failed --all >> /tmp/systemctl

ovsdb-client dump >> /tmp/ovsdb_dump
"""


class OpenSwitchNode(DockerNode):
    """
    Custom OpenSwitch node for the Topology Docker platform engine.

    This custom node loads an OpenSwitch image and has vtysh as default
    shell (in addition to bash).

    See :class:`topology_docker.node.DockerNode`.
    """

    def __init__(
            self, identifier,
            image='topology/ops:latest', binds=None,
            environment={'container': 'docker'},
            **kwargs):

        # Add binded directories
        container_binds = [
            '/dev/log:/dev/log',
            '/sys/fs/cgroup:/sys/fs/cgroup:ro'
        ]
        if binds is not None:
            container_binds.append(binds)

        super(OpenSwitchNode, self).__init__(
            identifier, image=image, command='/sbin/init',
            binds=';'.join(container_binds), hostname='switch',
            **kwargs
        )

        initial_prompt = '(^|\n).*[#$] '

        # Add vtysh (default) shell
        self._shells['vtysh'] = OpenSwitchVtyshShell(
            self.container_id, 'bash', initial_prompt=initial_prompt
        )

        # Add bash shells
        self._shells['bash'] = DockerBashShell(
            self.container_id, 'bash',
            initial_prompt=initial_prompt
        )
        self._shells['bash_swns'] = DockerBashShell(
            self.container_id, 'ip netns exec swns bash',
            initial_prompt=initial_prompt
        )
        self._shells['vsctl'] = DockerBashShell(
            self.container_id, 'bash',
            initial_prompt=initial_prompt,
            prefix='ovs-vsctl ', timeout=60
        )

    def notify_post_build(self):
        """
        Get notified that the post build stage of the topology build was
        reached.

        See :meth:`DockerNode.notify_post_build` for more information.
        """
        super(OpenSwitchNode, self).notify_post_build()
        self._setup_system()

    def _setup_system(self):
        """
        Setup the OpenSwitch image for testing.

        #. Wait for daemons to converge.
        #. Assign an interface to each port label.
        #. Create remaining interfaces.
        """

        # Write the log gathering script
        process_log = '{}/process_log.sh'.format(self.shared_dir)
        with open(process_log, "w") as fd:
            fd.write(PROCESS_LOG)
        check_call('chmod 755 {}/process_log.sh'.format(self.shared_dir),
                   shell=True)

        # Write and execute setup script
        setup_script = '{}/openswitch_setup.py'.format(self.shared_dir)
        with open(setup_script, 'w') as fd:
            fd.write(SETUP_SCRIPT)

        try:
            self._docker_exec('python {}/openswitch_setup.py -d'
                              .format(self.shared_dir_mount))
        except Exception as e:
            check_call('touch {}/logs'.format(self.shared_dir), shell=True)
            check_call('chmod 766 {}/logs'.format(self.shared_dir),
                       shell=True)
            self._docker_exec('/bin/bash {}/process_log.sh'
                              .format(self.shared_dir_mount))
            check_call(
                'tail -n 2000 /var/log/syslog > {}/syslog'.format(
                    self.shared_dir
                ), shell=True)
            check_call(
                'docker ps -a >> {}/logs'.format(self.shared_dir),
                shell=True
            )
            check_call('cat {}/logs'.format(self.shared_dir), shell=True)
            raise e

        # Read back port mapping
        port_mapping = '{}/port_mapping.json'.format(self.shared_dir)
        with open(port_mapping, 'r') as fd:
            mappings = loads(fd.read())

        if hasattr(self, 'ports'):
            self.ports.update(mappings)
            return
        self.ports = mappings

    def set_port_state(self, portlbl, state):
        """
        Set the given port label to the given state.

        See :meth:`DockerNode.set_port_state` for more information.
        """
        iface = self.ports[portlbl]
        state = 'up' if state else 'down'

        not_in_netns = self._docker_exec('ls /sys/class/net/').split()
        prefix = '' if iface in not_in_netns else 'ip netns exec swns'

        command = '{prefix} ip link set dev {iface} {state}'.format(**locals())
        self._docker_exec(command)

    def stop(self):
        """
        See :meth:`topology_docker.node.DockerNode.stop` for more information.

        This method attempts a clean exit from the vtysh shell.
        """
        self._shells['vtysh']._exit()
        super(OpenSwitchNode, self).stop()


__all__ = ['OpenSwitchNode']
