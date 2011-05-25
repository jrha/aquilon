# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
#
# Copyright (C) 2009,2010,2011  Contributor
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the EU DataGrid Software License.  You should
# have received a copy of the license with this program, and the
# license is published at
# http://eu-datagrid.web.cern.ch/eu-datagrid/license.html.
#
# THE FOLLOWING DISCLAIMER APPLIES TO ALL SOFTWARE CODE AND OTHER
# MATERIALS CONTRIBUTED IN CONNECTION WITH THIS PROGRAM.
#
# THIS SOFTWARE IS LICENSED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE AND ANY WARRANTY OF NON-INFRINGEMENT, ARE
# DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
# OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT
# OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. THIS
# SOFTWARE MAY BE REDISTRIBUTED TO OTHERS ONLY BY EFFECTIVELY USING
# THIS OR ANOTHER EQUIVALENT DISCLAIMER AS WELL AS ANY OTHER LICENSE
# TERMS THAT MAY APPLY.
"""Contains the logic for `aq update machine`."""

from aquilon.exceptions_ import NotFoundException
from aquilon.worker.broker import BrokerCommand
from aquilon.worker.dbwrappers.location import get_location
from aquilon.worker.dbwrappers.network import get_network_byname, get_network_byip
from aquilon.aqdb.model import Network, NetworkEnvironment


class CommandUpdateNetwork(BrokerCommand):

    def render(self, session, network, ip, network_environment, discovered,
               discoverable, type=False, **arguments):

        networks = []

        dbnet_env = NetworkEnvironment.get_unique_or_default(session,
                                                             network_environment)

        if network or ip:
            dbnetwork = network and get_network_byname(session, network,
                                                       dbnet_env) or None
            dbnetwork = ip and get_network_byip(session, ip, dbnet_env) or dbnetwork
            if not dbnetwork:
                raise NotFoundException('No valid network supplied.')
            networks.append(dbnetwork)
        else:
            q = session.query(Network)
            q = q.filter_by(network_environment=dbnet_env)
            if type:
                q = q.filter_by(network_type = type)
            dblocation = get_location(session, **arguments)
            if dblocation:
                q = q.filter_by(location=dblocation)
            networks.extend(q.all())
            if len(networks) <= 0:
                raise NotFoundException("No existing networks found with the "
                                        "specified network type or location.")

        for net in networks:
            if discoverable is not None:
                net.is_discoverable = discoverable
            if discovered is not None:
                net.is_discovered = discovered
            session.add(net)

        session.flush()
        return