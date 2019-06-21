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
OpenSwitch shell module
"""

from __future__ import unicode_literals, absolute_import
from __future__ import print_function, division

from logging import warning

from pexpect import EOF

from topology_docker.shell import DockerShell


class OpenSwitchVtyshShell(DockerShell):
    """
    OpenSwitch vtysh shell

    :param str container_id: identifier of the container that holds this shell
    """

    def __init__(self, container_id):
        super(OpenSwitchVtyshShell, self).__init__(
            container_id, 'vtysh', '(^|\n)switch(\([\-a-zA-Z0-9]*\))?#'
        )

    def _exit(self):
        """
        Attempt a clean exit from the shell.
        """
        try:
            self.send_command('end')
            self.send_command('exit', matches=[EOF])
        except Exception as error:
            warning(
                'Exiting the shell failed with this error: {}'.format(
                    str(error)
                )
            )


class OpenSwitchValgrindShell(DockerShell):
    """
    OpenSwitch valgrind shell

    :param str container_id: identifier of the container that holds this shell
    """

    def __init__(self, container_id):
        super(OpenSwitchValgrindShell, self).__init__(
            container_id, 'valgrind', '(^|\n)switch(\([\-a-zA-Z0-9]*\))?#'
        )

    def _exit(self):
        """
        Attempt a clean exit from the shell.
        """
        try:
            self.send_command('end')
            self.send_command('exit', matches=[EOF])
        except Exception as error:
            warning(
                'Exiting the shell failed with this error: {}'.format(
                    str(error)
                )
            )


__all__ = ['OpenSwitchVtyshShell', 'OpenSwitchValgrindShell']
