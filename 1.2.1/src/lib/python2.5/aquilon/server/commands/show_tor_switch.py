#!/ms/dist/python/PROJ/core/2.5.0/bin/python
# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# $Header$
# $Change$
# $DateTime$
# $Author$
# Copyright (C) 2008 Morgan Stanley
#
# This module is part of Aquilon
"""Contains the logic for `aq show tor_switch`."""


from aquilon.exceptions_ import ArgumentError
from aquilon.server.broker import (add_transaction, az_check, format_results,
                                   BrokerCommand)
from aquilon.server.dbwrappers.location import get_location
from aquilon.server.dbwrappers.model import get_model
from aquilon.aqdb.hardware import Machine


class CommandShowTorSwitch(BrokerCommand):

    @add_transaction
    @az_check
    @format_results
    def render(self, session, tor_switch, rack, model, **arguments):
        q = session.query(Machine)
        q = q.join(["model", "machine_type"]).filter_by(type="tor_switch")
        q = q.reset_joinpoint()
        if tor_switch:
            q = q.filter(Machine.name.like(tor_switch + '%'))
        if rack:
            dblocation = get_location(session, rack=rack)
            q = q.filter_by(location=dblocation)
        if model:
            dbmodel = get_model(session, model)
            if dbmodel.machine_type not in ['tor_switch']:
                raise ArgumentError("Requested model %s is a %s, not a tor_switch." %
                        (model, dbmodel.machine_type))
            q = q.filter_by(model=dbmodel)
        return q.all()


#if __name__=='__main__':
