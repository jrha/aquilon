#!/ms/dist/python/PROJ/core/2.5.0/bin/python
# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# $Header$
# $Change$
# $DateTime$
# $Author$
# Copyright (C) 2008 Morgan Stanley
#
# This module is part of Aquilon
""" Machine Specifications: the rows of this table represent the default
    values of machine "models" so that users don't need to manaully enter the
    low level details of each one since this is mostly repeated data in large
    grid deployments, such as Saphire """


from datetime import datetime
import sys
import os

if __name__ == '__main__':
    DIR = os.path.dirname(os.path.realpath(__file__))
    sys.path.insert(0, os.path.realpath(os.path.join(DIR, '..', '..', '..')))
    import aquilon.aqdb.depends

from sqlalchemy import (Table, Column, Integer, DateTime, Sequence, String,
                        select, ForeignKey, PassiveDefault, UniqueConstraint)
from sqlalchemy.orm import relation, backref, deferred

from aquilon.aqdb.db_factory   import Base
from aquilon.aqdb.hw.model     import Model
from aquilon.aqdb.hw.vendor    import Vendor
from aquilon.aqdb.hw.cpu       import Cpu
from aquilon.aqdb.hw.disk_type import DiskType


class MachineSpecs(Base):
    """ Captures the configuration hardware components for a given model """
    #TODO: Maybe this entire table is in fact a part of the model "subtype"

    _def_cpu_cnt = { 'workstation':1, 'blade': 2, 'rackmount' : 4 }
    _def_nic_cnt = { 'workstation':1, 'blade': 2, 'rackmount' : 2 }
    _def_memory  = { 'workstation': 2048, 'blade': 8192, 'rackmount': 16384 }

    __tablename__ = 'machine_specs'
    id            = Column( Integer,
                           Sequence('machine_specs_seq'),
                                    primary_key=True)

    model_id      = Column(Integer,
                           ForeignKey('model.id', name = 'mach_spec_model_fk'),
                           nullable = False)

    cpu_id        = Column(Integer,
                           ForeignKey('cpu.id', name = 'mach_spec_cpu_fk'),
                           nullable = False)

    cpu_quantity  = Column(Integer, nullable = False) #Constrain to below 512?

    memory        = Column(Integer, nullable = False, default = 0)

    disk_type_id  = Column(Integer,
                           ForeignKey('disk_type.id',
                                      name = 'mach_spec_disk_typ_fk'),
                           nullable=False)

    disk_capacity = Column(Integer, nullable = False, default = 36)

    nic_count     = Column(Integer, nullable = False, default = 2)

    creation_date = deferred(
        Column('creation_date', DateTime, default=datetime.now))

    comments      = deferred(
        Column('comments', String(255), nullable=True))

    model         = relation(Model, backref=backref('machine_specs',
                                                    uselist=False))
    cpu           = relation(Cpu)
    disk_type     = relation(DiskType)


machine_specs = MachineSpecs.__table__

machine_specs.primary_key.name = 'machine_specs_pk'
#for now, need a UK on model_id. WILL be a name AND a model_id as UK.
machine_specs.append_constraint(
    UniqueConstraint('model_id', name = 'machine_spec_model_id_uk'))


def populate(*args, **kw):
    from aquilon.aqdb.db_factory import db_factory, Base
    from sqlalchemy import insert

    dbf = db_factory()
    Base.metadata.bind = dbf.engine
    if 'debug' in args:
        Base.metadata.bind.echo = True

    s = dbf.session()

    machine_specs.create(checkfirst=True)

    if Base.metadata.bind.echo == True:
        Base.metadata.bind.echo == False


def populate_needs_to_be_fixed():
    if len(s.query(MachineSpecs).all()) < 1:

        a=MachineSpecs(model='hs20',cpu='xeon_2660',comments='FAKE')

        b=MachineSpecs(model='hs21',cpu='xeon_2660',
                                disk_capacity=68, comments='FAKE')

        c=MachineSpecs(model='poweredge_6650', cpu='xeon_3000',cpu_quantity=4,
                                comments='FAKE')

        d=MachineSpecs(model='bl45p',cpu='opteron_2600',memory=32768,
                                comments='FAKE')

        e=MachineSpecs(model='bl260c', cpu='xeon_2500', memory=24576)

        f=MachineSpecs(model='vb1205xm', cpu='xeon_2500', memory=24576)

        for ms in [a, b, c, d, e, f]:
            try:
                Session.save(ms)
            except Exception,e:
                Session.rollback()
                print 'Saving:', e
                continue
            try:
                Session.commit()
            except Exception,e:
                Session.rollback()
                print 'Commiting ',e
                continue
