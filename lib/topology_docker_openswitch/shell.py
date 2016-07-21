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

from topology_docker.shell import DockerBashShell


class OpenSwitchVtyshShell(DockerBashShell):
    """
    OpenSwitch vtysh shell

    :param str container_id: identifier of the container that holds this shell
    """

    FORCED_PROMPT = 'X@~~==::VTYSH_PROMPT::==~~@X'

    def _setup_shell(self, connection=None):
        """
        FIXME: Document this
        """

        super(OpenSwitchVtyshShell, self)._setup_shell(connection=connection)

        spawn = self._get_connection(connection)

        spawn.expect(DockerBashShell.FORCED_PROMPT)

        # This disables the terminal echoing of commands, it also removes the
        # echo inside the vtysh shell
        spawn.sendline('stty -echo')

        spawn.expect(DockerBashShell.FORCED_PROMPT)

        spawn.sendline('vtysh')

        prompt_tpl = '{}(\([\-a-zA-Z0-9]*\))?#'

        spawn.expect(prompt_tpl.format('switch'))

        spawn.sendline('set prompt {}'.format(self.FORCED_PROMPT))

        self._prompt = prompt_tpl.format(self.FORCED_PROMPT)

    def _exit(self):
        """
        Attempt a clean exit from the shell.
        """
        try:
            self.send_command('end')
            self.send_command(
                'exit', matches=[EOF, DockerBashShell.FORCED_PROMPT]
            )
        except Exception as error:
            warning(
                'Exiting the shell failed with this error: {}'.format(
                    str(error)
                )
            )


__all__ = ['OpenSwitchVtyshShell']
