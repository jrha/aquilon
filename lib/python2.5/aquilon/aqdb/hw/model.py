#!/ms/dist/python/PROJ/core/2.5.0/bin/python
""" Vendor and Model are representations of the various manufacturers and
    the asset inventory of the kinds of machines we use in the plant """


from datetime import datetime
import sys
import os

if __name__ == '__main__':
    DIR = os.path.dirname(os.path.realpath(__file__))
    sys.path.insert(0, os.path.realpath(os.path.join(DIR, '..', '..', '..')))
    import aquilon.aqdb.depends

from sqlalchemy import (MetaData, create_engine, UniqueConstraint, Table,
                        Integer, DateTime, Sequence, String, select,
                        Column, ForeignKey, PassiveDefault)
from sqlalchemy.orm import relation, deferred

from aquilon.aqdb.column_types.aqstr import AqStr
from aquilon.aqdb.db_factory import Base
from aquilon.aqdb.hw.vendor import Vendor


class Model(Base):
    __tablename__ = 'model'
    id = Column(Integer, Sequence('model_id_seq'), primary_key=True)
    name = Column(String(64))

    vendor_id = Column(Integer,
                       ForeignKey('vendor.id', name = 'model_vendor_fk'),
                       nullable = False)
    machine_type = Column(AqStr(16), nullable = False)

    creation_date = deferred(Column(DateTime, default=datetime.now,
                                    nullable = False))
    comments = deferred(Column(String(255)))

    vendor = relation(Vendor)

model = Model.__table__
model.primary_key.name = 'model_pk'

model.append_constraint(UniqueConstraint('name','vendor_id',
                                   name = 'model_name_vendor_uk'))

table = model

def populate(db, *args, **kw):
    s = db.session()
    mlist=s.query(Model).all()

    if not mlist:

        f = [['ibm', 'hs20-884345u', 'blade'],
            ['ibm', 'ls20-8850pap', 'blade'],
            ['ibm', 'hs21-8853l5u', 'blade'],
            ['ibm', 'bce', 'chassis'],
            ['ibm', 'bch', 'chassis'],
            ['ibm', 'dx320-6388ac1', 'rackmount'], #one of the 4 in 1 types
            ['ibm', 'dx320-6388dau', 'rackmount'],
            ['hp',  'bl35p','blade'],
            ['hp',  'bl465c','blade'],
            ['hp',  'bl480c','blade'],
            ['hp',  'bl680c','blade'],
            ['hp',  'bl685c','blade'],
            ['hp',  'dl145','rackmount'],
            ['hp',  'dl580','rackmount'],
            ['hp',  'bl45p','blade'],
            ['hp',  'bl260c','blade'],
            ['hp',  'c-class', 'chassis'],
            ['hp',  'p-class', 'chassis'],
            ['verari', 'vb1205xm', 'blade'],
            ['sun','ultra-10','workstation'],
            ['dell','poweredge_6850','rackmount'],
            ['dell','poweredge_6650', 'rackmount'],
            ['dell','poweredge_2650','rackmount'],
            ['dell','poweredge_2850','rackmount'],
            ['dell','optiplex_260','workstation'],
            ['bnt','rs g8000','tor_switch'],
            ['cisco','ws-c2960-48tt-l','tor_switch'],
            ['aurora_vendor', 'aurora_chassis_model', 'aurora_chassis'],
            ['aurora_vendor', 'aurora_model', 'aurora_node']]

        for i in f:
            m = Model(name = i[1],
                      vendor = s.query(Vendor).filter_by(name =i[0]).first(),
                      machine_type = i[2])
            s.add(m)
        try:
            s.commit()
        except Exception,e:
            print e
        finally:
            s.close()
        print 'created models %s'%(s.query(Model).all())

# Copyright (C) 2008 Morgan Stanley
# This module is part of Aquilon

# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
