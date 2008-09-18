#!/ms/dist/python/PROJ/core/2.5.0/bin/python
# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# Copyright (C) 2008 Morgan Stanley
#
# This module is part of Aquilon
"""Contains the logic for `aq show manager --missing`."""


from aquilon.server.broker import (format_results, add_transaction, az_check,
                                   BrokerCommand)
from aquilon.server.formats.interface import MissingManagersList
from aquilon.aqdb.hw.interface import Interface


class CommandShowManagerMissing(BrokerCommand):

    @add_transaction
    @az_check
    @format_results
    def render(self, session, **arguments):
        q = session.query(Interface)
        q = q.filter_by(interface_type='management')
        q = q.filter(Interface.system==None)
        q = q.join('hardware_entity')
        q = q.filter_by(hardware_entity_type='machine')
        return MissingManagersList(q.all())


#if __name__=='__main__':
