# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008,2009,2010,2011,2012,2013  Contributor
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
"""Contains the logic for `aq add dns_domain`."""


from aquilon.worker.broker import BrokerCommand  # pylint: disable=W0611
from aquilon.aqdb.model import DnsDomain
from aquilon.worker.processes import DSDBRunner


class CommandAddDnsDomain(BrokerCommand):

    required_parameters = ["dns_domain"]

    def render(self, session, logger, dns_domain, restricted, comments,
               **arguments):
        DnsDomain.get_unique(session, dns_domain, preclude=True)

        dbdns_domain = DnsDomain(name=dns_domain, comments=comments)
        if restricted:
            dbdns_domain.restricted = True
        session.add(dbdns_domain)
        session.flush()

        dsdb_runner = DSDBRunner(logger=logger)
        dsdb_runner.add_dns_domain(dbdns_domain.name, comments)
        dsdb_runner.commit_or_rollback()

        return
