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
""" The module governing tables and objects that represent IP networks in
    Aquilon. """
from datetime import datetime
from ipaddr import (IPv4Address, IPv4Network, AddressValueError,
                    NetmaskValueError)
import logging

from sqlalchemy import (Column, Integer, Sequence, String, DateTime, ForeignKey,
                        UniqueConstraint, CheckConstraint, Index, desc, event)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relation, deferred, reconstructor, validates
from sqlalchemy.pool import Pool
from sqlalchemy.sql import and_

from aquilon.exceptions_ import NotFoundException, InternalError
from aquilon.aqdb.model import Base, Location, NetworkEnvironment
from aquilon.aqdb.column_types import AqStr, IPV4
from aquilon.config import Config

LOGGER = logging.getLogger(__name__)
_TN = "network"


class NetworkProperties(object):
    """ Container class for attributes derived from the network's type """

    @staticmethod
    def get_str(config, network_type, option, default=None):
        section = "network_" + network_type
        if config.has_option(section, option):
            return config.get(section, option)
        else:
            default_section = "network_" + config.get("broker",
                                                      "default_network_type")
            if config.has_option(default_section, option):
                return config.get(default_section, option)
            else:
                return default

    @staticmethod
    def get_int(config, network_type, option, default=None):
        section = "network_" + network_type
        if config.has_option(section, option):
            return config.getint(section, option)
        else:
            default_section = "network_" + config.get("broker",
                                                      "default_network_type")
            if config.has_option(default_section, option):
                return config.getint(default_section, option)
            else:
                return default

    def __init__(self, config, network_type):
        self.default_gateway_offset = self.get_int(config, network_type,
                                                   "default_gateway_offset", 1)
        self.first_usable_offset = self.get_int(config, network_type,
                                                "first_usable_offset", 2)
        reserved_str = self.get_str(config, network_type, "reserved_offsets")
        self.reserved_offsets = [int(idx.strip()) for idx in
                                 reserved_str.split(",")]


class Network(Base):
    """ Represents subnets in aqdb.  Network Type can be one of four values
        which have been carried over as legacy from the network table in DSDB:

        *   management: no networks have it(@ 3/27/08), it's probably useless

        *   transit: for the phyical interfaces of zebra nodes

        *   vip:     for the zebra addresses themselves

        *   unknown: for network rows in DSDB with NULL values for 'type'

        *   tor_net: tor switches are managed in band, which means that
                     if you know the ip/netmask of the switch, you know the
                     network which it provides for, and the 5th and 6th address
                     are reserved for a dynamic pool for the switch on the net
        *   stretch and vpls: networks that exist in more than one location
        *   external/external_vendor
        *   heartbeat
        *   wan
        *   campus
    """

    __tablename__ = _TN

    # Class-level cache of properties bound to the network type
    network_type_map = {}

    # Default network properties
    default_network_props = None

    id = Column(Integer, Sequence('%s_id_seq' % _TN), primary_key=True)

    network_environment_id = Column(Integer,
                                    ForeignKey('network_environment.id',
                                               name='%s_net_env_fk' % _TN),
                                    nullable=False)

    location_id = Column(Integer,
                         ForeignKey('location.id', name='%s_loc_fk' % _TN),
                         nullable=False)

    network_type = Column(AqStr(32), nullable=False)
    cidr = Column(Integer, nullable=False)
    name = Column(AqStr(255), nullable=False)
    ip = Column(IPV4, nullable=False)
    side = Column(AqStr(4), nullable=True, default='a')

    creation_date = deferred(Column(DateTime, default=datetime.now,
                                    nullable=False))

    comments = deferred(Column(String(255), nullable=True))

    network_environment = relation(NetworkEnvironment)

    location = relation(Location)

    # The routers relation is defined in router_address.py
    router_ips = association_proxy("routers", "ip")

    __table_args__ = (UniqueConstraint(network_environment_id, ip,
                                       name='%s_net_env_ip_uk' % _TN),
                      CheckConstraint(and_(cidr >= 1, cidr <= 32),
                                      name="%s_cidr_ck" % _TN),
                      Index('%s_location_idx' % _TN, location_id))

    def __init__(self, network=None, network_type=None, **kw):
        # pylint: disable=W0621
        if not isinstance(network, IPv4Network):
            raise InternalError("Expected an IPv4Network, got: %s" %
                                type(network))

        if not network_type:
            config = Config()
            network_type = config.get("broker", "default_network_type")

        self._network = network
        self._props = self.network_type_map.get(self.network_type,
                                                self.default_network_props)

        super(Network, self).__init__(ip=network.network,
                                      cidr=network.prefixlen,
                                      network_type=network_type, **kw)

    @reconstructor
    def _init_db(self):
        # This function gets called instead of __init__ when an object is loaded
        # from the database
        self._network = None
        self._props = self.network_type_map.get(self.network_type,
                                                self.default_network_props)

    @property
    def first_usable_host(self):
        start = self._props.first_usable_offset

        # TODO: do we need this fallback for /31 and /32 networks?
        if self.network.numhosts < start:
            start = 0

        return self.network[start]

    @property
    def reserved_offsets(self):
        return self._props.reserved_offsets

    @property
    def default_gateway_offset(self):
        return self._props.default_gateway_offset

    @property
    def network(self):
        if not self._network:
            # TODO: more efficient initialization? Using
            # IPv4Network(int(self.ip)).supernet(new_prefix=self.cidr) looks
            # promising at first, but unfortunately it uses the same string
            # conversion internally...
            self._network = IPv4Network("%s/%s" % (self.ip, self.cidr))
        return self._network

    @network.setter
    def network(self, value):
        if not isinstance(value, IPv4Network):
            raise InternalError("Expected an IPv4Network, got: %s" %
                                type(network))
        self._network = value
        self.ip = value.network
        self.cidr = value.prefixlen

    @validates('ip', 'cidr')
    def _reset_network(self, attr, value):  # pylint: disable=W0613
        # Make sure the network object will get re-computed if the parameters
        # change
        self._network = None
        return value

    @property
    def netmask(self):
        return self.network.netmask

    @property
    def broadcast(self):
        return self.network.broadcast

    @property
    def available_ip_count(self):
        return int(self.broadcast) - int(self.first_usable_host)

    @property
    def is_internal(self):
        return self.network_environment.is_default

    def __le__(self, other):
        if self.network_environment_id != other.network_environment_id:
            return NotImplemented
        return self.ip.__le__(other.ip)

    def __lt__(self, other):
        if self.network_environment_id != other.network_environment_id:
            return NotImplemented
        return self.ip.__lt__(other.ip)

    def __ge__(self, other):
        if self.network_environment_id != other.network_environment_id:
            return NotImplemented
        return self.ip.__ge__(other.ip)

    def __gt__(self, other):
        if self.network_environment_id != other.network_environment_id:
            return NotImplemented
        return self.ip.__gt__(other.ip)

    @classmethod
    def get_unique(cls, session, *args, **kwargs):
        # Fall back to the generic implementation unless the caller used exactly
        # one non-keyword argument.  Any caller using preclude would be passing
        # keywords anyway.
        compel = kwargs.pop("compel", False)
        options = kwargs.pop("query_options", None)
        netenv = kwargs.pop("network_environment", None)
        if kwargs or len(args) > 1:
            return super(Network, cls).get_unique(session, *args,
                                                  network_environment=netenv,
                                                  query_options=options,
                                                  compel=compel, **kwargs)

        # Just a single positional argumentum - do magic
        # The order matters here, we don't want to parse '1.2.3.4' as
        # IPv4Network('1.2.3.4/32')
        ip = None
        if isinstance(args[0], IPv4Address):
            ip = args[0]
        else:
            try:
                ip = IPv4Address(args[0])
            except AddressValueError:
                pass

        if ip:
            return super(Network, cls).get_unique(session, ip=ip,
                                                  network_environment=netenv,
                                                  query_options=options,
                                                  compel=compel)
        net = None
        if isinstance(args[0], IPv4Network):
            net = args[0]
        else:
            try:
                net = IPv4Network(args[0])
            except (AddressValueError, NetmaskValueError):
                pass
        if net:
            return super(Network, cls).get_unique(session, ip=net.network,
                                                  cidr=net.prefixlen,
                                                  network_environment=netenv,
                                                  query_options=options,
                                                  compel=compel)

        return super(Network, cls).get_unique(session, name=args[0],
                                              network_environment=netenv,
                                              query_options=options,
                                              compel=compel)

    def __format__(self, format_spec):
        if format_spec != "a":
            return super(Network, self).__format__(format_spec)
        return "%s [%s]" % (self.name, self.network)

    def __repr__(self):
        msg = '<Network '

        if self.name != self.network:
            msg += '%s ip=' % (self.name)

        msg += '%s (netmask=%s), type=%s, side=%s, located in %s, environment=%s>' % (
            str(self.network), str(self.network.netmask), self.network_type,
            self.side, format(self.location), self.network_environment)
        return msg

    @property
    def vlans_guest_count(self):
        return sum([vlan.guest_count for vlan in self.observed_vlans])

    @property
    def is_at_guest_capacity(self):
        return self.vlans_guest_count >= self.available_ip_count

network = Network.__table__  # pylint: disable=C0103
network.info['unique_fields'] = ['network_environment', 'ip']
network.info['extra_search_fields'] = ['name', 'cidr']


def get_net_id_from_ip(session, ip, network_environment=None):
    """Requires a session, and will return the Network for a given ip."""
    if ip is None:
        return None

    if isinstance(network_environment, NetworkEnvironment):
        dbnet_env = network_environment
    else:
        dbnet_env = NetworkEnvironment.get_unique_or_default(session,
                                                             network_environment)

    # Query the last network having an address smaller than the given ip. There
    # is no guarantee that the returned network does in fact contain the given
    # ip, so this must be checked separately.
    subq = session.query(Network.ip)
    subq = subq.filter_by(network_environment=dbnet_env)
    subq = subq.filter(Network.ip <= ip)
    subq = subq.order_by(desc(Network.ip)).limit(1)
    q = session.query(Network)
    q = q.filter_by(network_environment=dbnet_env)
    q = q.filter(Network.ip == subq.as_scalar())
    net = q.first()
    if not net or not ip in net.network:
        raise NotFoundException("Could not determine network containing IP "
                                "address %s." % ip)
    return net


# This is a hack. We have to call discover_network_types() after the
# configuration has been parsed, and that surely happens before the first DB
# connection
@event.listens_for(Pool, 'first_connect')
def discover_network_types(dbapi_con, connection_record):  # pylint: disable=W0613
    config = Config()
    if not config.has_option("broker", "default_network_type"):  # pragma: no cover
        raise InternalError("The default_network_type option is missing from "
                            "the [broker] section in the configuration.")

    default_type = config.get("broker", "default_network_type")
    default_section = "network_" + default_type
    if not config.has_section(default_section):  # pragma: no cover
        raise InternalError("The default network type is %s, but there's no "
                            "section named [%s] in the configuration." %
                            (default_type, default_section))

    nettypes = {}

    # This function should be called only once, but you never know...
    if Network.network_type_map:
        return

    for section in config.sections():
        if not section.startswith("network_"):
            continue
        name = section[8:]
        nettypes[name] = NetworkProperties(config, name)
        LOGGER.info("Configured network type %s" % name)

    Network.network_type_map = nettypes
    Network.default_network_props = nettypes[default_type]
