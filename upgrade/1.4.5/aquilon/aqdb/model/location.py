# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008,2009,2010,2013  Contributor
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
""" The Location structures represent  """

from datetime import datetime

from sqlalchemy import (Table, Integer, DateTime, Sequence, String, Column,
                        ForeignKey, UniqueConstraint, text)

from sqlalchemy.orm import deferred, relation, backref, object_session

from aquilon.aqdb.model import Base
from aquilon.aqdb.column_types.aqstr import AqStr

class Location(Base):
    __tablename__ = 'location'

    id = Column(Integer, Sequence('location_id_seq'), primary_key=True)

    name = Column(AqStr(16), nullable=False)

    #code = Column(AqStr(16), nullable=False) #how to override the __init__?

    parent_id = Column(Integer, ForeignKey(
        'location.id', name='loc_parent_fk'), nullable=True)

    location_type = Column(AqStr(32), nullable=False)

    #location_type_id = Column(Integer, ForeignKey(
    #    'location_type.id', ondelete='CASCADE',
    #    name='sli_loc_typ__fk'), nullable=False)

    fullname = Column(String(255), nullable=False)

    creation_date = deferred(Column(DateTime, default=datetime.now,
                                    nullable=False))
    comments = deferred(Column(String(255), nullable=True))

    __mapper_args__ = {'polymorphic_on' : location_type}

    def get_parents(loc):
        pl=[]
        p_node=loc.parent
        if not p_node:
            return pl
        while p_node.parent is not None and p_node.parent != p_node:
            pl.append(p_node)
            p_node=p_node.parent
        pl.append(p_node)
        pl.reverse()
        return pl

    def get_p_dict(loc):
        d={}
        p_node=loc
        while p_node.parent is not None and p_node.parent != p_node:
            d[str(p_node.location_type)]=p_node
            p_node=p_node.parent
        return d

    def _parents(self):
        return self.get_parents()
    parents = property(_parents)

    def _p_dict(self):
        return self.get_p_dict()
    p_dict = property(_p_dict)

    def _hub(self):
        return self.p_dict.get('hub', None)
    hub = property(_hub)

    def _continent(self):
        return self.p_dict.get('continent', None)
    continent=property(_continent)

    def _country(self):
        return self.p_dict.get('country', None)
    country = property(_country)

    def _campus(self):
        return self.p_dict.get('campus', None)
    campus = property(_campus)

    def _city(self):
        return self.p_dict.get('city', None)
    city = property(_city)

    def _building(self):
        return self.p_dict.get('building', None)
    building = property(_building)

    def _rack(self):
        return self.p_dict.get('rack', None)
    rack = property(_rack)

    def _chassis(self):
        return self.p_dict.get('chassis', None)
    chassis = property(_chassis)

    def append(self,node):
        if isinstance(node, Location):
            node.parent = self
            self.sublocations[node] = node

    def sysloc(self):
        if str(self.location_type) in ['building', 'rack', 'chassis', 'desk']:
            return str('.'.join([str(self.p_dict[item]) for item in
                ['building', 'city', 'continent']]))

    def _children(self):
        s = text("""select * from location
                    where id != %d
                    connect by parent_id = prior id
                    start with id = %d"""%(self.id,self.id))

        return object_session(self).query(Location).from_statement(s).all()

    children = property(_children)

    def typed_children(self,typ):
        s = text("""select * from location
                    where location_type = '%s'
                    connect by parent_id = prior id
                    start with id = %d"""%(typ, self.id))

        return object_session(self).query(Location).from_statement(s).all()

    def __repr__(self):
        return self.__class__.__name__ + " " + str(self.name)

    def __str__(self):
        return str(self.name)

location = Location.__table__

location.primary_key.name = 'location_pk'

location.append_constraint(
    UniqueConstraint('name', 'location_type', name='loc_name_type_uk'))

Location.sublocations = relation('Location',
                                 backref=backref('parent',
                                                 remote_side=[location.c.id],))

table = location


