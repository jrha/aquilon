# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008,2009,2010,2011,2012,2013,2014,2015  Contributor
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Contains the logic for `aq map service`."""

from aquilon.worker.broker import BrokerCommand
from aquilon.aqdb.model import (Personality, ServiceMap, ServiceInstance,
                                NetworkEnvironment)
from aquilon.worker.dbwrappers.change_management import validate_prod_personality
from aquilon.worker.dbwrappers.location import get_location
from aquilon.worker.dbwrappers.network import get_network_byip


class CommandMapService(BrokerCommand):

    required_parameters = ["service", "instance"]

    def doit(self, session, dbmap, dbinstance, dblocation, dbnetwork,
             dbpersona):
        if not dbmap:
            dbmap = ServiceMap(service_instance=dbinstance, location=dblocation,
                               network=dbnetwork, personality=dbpersona)
            session.add(dbmap)

    def render(self, session, service, instance, archetype, personality,
               networkip, justification, reason, user, **kwargs):
        dbinstance = ServiceInstance.get_unique(session, service=service,
                                                name=instance, compel=True)
        dblocation = get_location(session, **kwargs)

        if networkip:
            dbnet_env = NetworkEnvironment.get_unique_or_default(session)
            dbnetwork = get_network_byip(session, networkip, dbnet_env)
        else:
            dbnetwork = None

        if personality:
            dbpersona = Personality.get_unique(session, name=personality,
                                               archetype=archetype, compel=True)

            for dbstage in dbpersona.stages.values():
                validate_prod_personality(dbstage, user, justification, reason)
        else:
            dbpersona = None

        q = session.query(ServiceMap)
        q = q.filter_by(service_instance=dbinstance,
                        location=dblocation, network=dbnetwork,
                        personality=dbpersona)

        dbmap = q.first()
        self.doit(session, dbmap, dbinstance, dblocation, dbnetwork, dbpersona)

        session.flush()

        return
