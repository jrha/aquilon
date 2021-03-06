# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2009,2010,2011,2012,2013  Contributor
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
"""Contains the logic for `aq del required service --personality`."""


from aquilon.exceptions_ import NotFoundException
from aquilon.worker.broker import BrokerCommand  # pylint: disable=W0611
from aquilon.aqdb.model import Personality, Service


class CommandDelRequiredServicePersonality(BrokerCommand):

    required_parameters = ["service", "archetype", "personality"]

    def render(self, session, service, archetype, personality, **arguments):
        dbpersonality = Personality.get_unique(session, name=personality,
                                               archetype=archetype, compel=True)
        dbservice = Service.get_unique(session, service, compel=True)
        try:
            dbservice.personalities.remove(dbpersonality)
        except ValueError:
            raise NotFoundException("Service %s required for archetype "
                                    "%s, personality %s not found." %
                                    (service, archetype, personality))
        session.flush()
        return
