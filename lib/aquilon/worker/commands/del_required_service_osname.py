# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2015  Contributor
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
"""Contains the logic for `aq del required service --osname`."""

from aquilon.exceptions_ import NotFoundException
from aquilon.worker.broker import BrokerCommand  # pylint: disable=W0611
from aquilon.worker.commands.add_required_service_osname import \
        CommandAddRequiredServiceOsname


class CommandDelRequiredServiceOsname(CommandAddRequiredServiceOsname):

    required_parameters = ["service", "archetype", "osname", "osversion"]

    def _update_dbobj(self, dbos, dbservice):
        try:
            dbos.required_services.remove(dbservice)
        except ValueError:
            raise NotFoundException("{0} required for {1:l} not found."
                                    .format(dbservice, dbos))