# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2009,2013  Contributor
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
""" Personality as a high level cfg object """
from datetime import datetime

from sqlalchemy import (Column, Integer, DateTime, Sequence, String, ForeignKey,
                        UniqueConstraint)
from sqlalchemy.sql import select
from sqlalchemy.orm import relation, deferred
from sqlalchemy.orm.session import object_session

from aquilon.aqdb.model import Base, Archetype
from aquilon.aqdb.column_types.aqstr import AqStr

_ABV = 'prsnlty'
_TN  = 'personality'

class Personality(Base):
    """ Personality names """
    __tablename__  = _TN

    id = Column(Integer, Sequence('%s_seq'%(_ABV)), primary_key=True)
    name = Column(AqStr(32), nullable=False)
    archetype_id = Column(Integer, ForeignKey(
        'archetype.id', name='%s_arch_fk'%(_ABV)), nullable=False)

    creation_date = Column(DateTime, default=datetime.now, nullable=False)
    comments = Column(String(255), nullable=True)

    archetype = relation(Archetype, backref='personality', uselist=False)

    def __repr__(self):
        s = ("<"+self.__class__.__name__ + " name ='"+ self.name +
             "', " + str(self.archetype) +'>')
        return s

    @classmethod
    def by_archetype(cls, dbarchetype):
        session = object_session(dbarchetype)
        return session.query(cls).filter(
            cls.__dict__['archetype'] == dbarchetype).all()


personality = Personality.__table__
table       = Personality.__table__


personality.primary_key.name='%s_pk'%(_ABV)
personality.append_constraint(UniqueConstraint('name', 'archetype_id',
                                               name='%s_uk'%(_TN)))

def populate(sess, *args, **kw):
    if len(sess.query(Personality).all()) > 0:
        return

    import os

    cfg_base = kw['cfg_base']
    assert os.path.isdir(cfg_base), "No such directory '%s'"%(cfg_base)

    for arch in sess.query(Archetype).all():
        #find aquilon archetype and all directories under it
        #change if we grow past having multiple archtypes w/ personalities
        if arch.name == 'aquilon':
            p = os.path.join(cfg_base, arch.name, 'personality')
            assert os.path.isdir(p), \
                    "Can't find personality directory '%s' in populate" % p
            for i in os.listdir(p):
                if os.path.isdir(os.path.abspath(os.path.join(p, i))):
                    pers = Personality(name=i, archetype=arch)
                    sess.add(pers)
        else:
            pers = Personality(name='generic', archetype=arch)
            sess.add(pers)

    try:
        sess.commit()
    except Exception, e:
        sess.rollback()
        raise e

    a = sess.query(Personality).first()
    assert(a)


