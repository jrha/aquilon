# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
#
# Copyright (C) 2008,2009,2010,2011  Contributor
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the EU DataGrid Software License.  You should
# have received a copy of the license with this program, and the
# license is published at
# http://eu-datagrid.web.cern.ch/eu-datagrid/license.html.
#
# THE FOLLOWING DISCLAIMER APPLIES TO ALL SOFTWARE CODE AND OTHER
# MATERIALS CONTRIBUTED IN CONNECTION WITH THIS PROGRAM.
#
# THIS SOFTWARE IS LICENSED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE AND ANY WARRANTY OF NON-INFRINGEMENT, ARE
# DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
# OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT
# OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. THIS
# SOFTWARE MAY BE REDISTRIBUTED TO OTHERS ONLY BY EFFECTIVELY USING
# THIS OR ANOTHER EQUIVALENT DISCLAIMER AS WELL AS ANY OTHER LICENSE
# TERMS THAT MAY APPLY.
"""Any work by the broker to write out (or read in?) templates lives here."""


import logging

from sqlalchemy.orm.session import object_session

from aquilon.config import Config
from aquilon.exceptions_ import IncompleteError, InternalError
from aquilon.aqdb.model import (Host, AddressAssignment, VlanInterface,
                                BondingInterface, BridgeInterface)
from aquilon.worker.locks import CompileKey
from aquilon.worker.templates.base import Plenary, PlenaryCollection
from aquilon.worker.templates.machine import PlenaryMachineInfo
from aquilon.worker.templates.cluster import PlenaryClusterClient
from aquilon.worker.templates.panutils import pan, StructureTemplate

LOGGER = logging.getLogger(__name__)

# Select the closest (i.e. in the same building) router
def select_router(dbmachine, routers):
    # Safe default
    gateway = routers[0].ip

    dbbuilding = dbmachine.location and dbmachine.location.building or None
    for router in routers:
        if router.location and router.location.building and \
           router.location.building == dbbuilding:
            gateway = router.ip
            break

    return gateway


class PlenaryHost(PlenaryCollection):
    """
    A facade for Toplevel and Namespaced Hosts (below).

    This class creates either/both toplevel and namespaced host plenaries,
    based on broker configuration:
    namespaced_host_profiles (boolean):
      if namespaced profiles should be generated
    flat_host_profiles (boolean):
      if host profiles should be put into a "flat" toplevel (non-namespaced)
    """
    def __init__(self, dbhost, logger=LOGGER):
        if not isinstance(dbhost, Host):
            raise InternalError("PlenaryHost called with %s instead of Host" %
                                dbhost.__class__.name)
        PlenaryCollection.__init__(self, logger=logger)
        self.config = Config()
        if self.config.getboolean("broker", "namespaced_host_profiles"):
            self.plenaries.append(PlenaryNamespacedHost(dbhost, logger=logger))
        if self.config.getboolean("broker", "flat_host_profiles"):
            self.plenaries.append(PlenaryToplevelHost(dbhost, logger=logger))

    def write(self, dir=None, user=None, locked=False, content=None):
        # Standard PlenaryCollection swallows IncompleteError.  If/when
        # the Host plenaries no longer raise that error this override
        # should be removed.
        total = 0
        for plenary in self.plenaries:
            total += plenary.write(dir=dir, user=user, locked=locked,
                                   content=content)
        return total


class PlenaryToplevelHost(Plenary):
    """
    A plenary template for a host, stored at the toplevel of the profiledir
    """
    def __init__(self, dbhost, logger=LOGGER):
        Plenary.__init__(self, dbhost, logger=logger)
        self.dbhost = dbhost
        # Store the branch separately so get_key() works even after the dbhost
        # object has been deleted
        self.branch = dbhost.branch.name
        self.name = dbhost.fqdn
        self.plenary_core = ""
        self.plenary_template = "%(name)s" % self.__dict__
        self.template_type = "object"
        self.dir = "%s/domains/%s/profiles" % (
            self.config.get("broker", "builddir"), self.branch)

    def will_change(self):
        # Need to override to handle IncompleteError...
        self.stash()
        if not self.new_content:
            try:
                self.new_content = self._generate_content()
            except IncompleteError:
                # Attempting to have IncompleteError thrown later by
                # not caching the return
                return self.old_content is None
        return self.old_content != self.new_content

    def get_key(self):
        # Going with self.name instead of self.plenary_template seems like
        # the right decision here - easier to predict behavior when meshing
        # with other CompileKey generators like PlenaryMachine.
        return CompileKey(domain=self.branch, profile=self.name,
                          logger=self.logger)

    def body(self, lines):
        session = object_session(self.dbhost)

        interfaces = dict()
        vips = dict()
        transit_interfaces = []
        routers = {}
        default_gateway = None
        dbmachine = self.dbhost.machine

        # FIXME: Enforce that one of the interfaces is marked boot?
        for dbinterface in self.dbhost.machine.interfaces:
            # Management interfaces are not configured at the host level
            if dbinterface.interface_type == 'management':
                continue

            ifdesc = {}

            if dbinterface.master:
                ifdesc["bootproto"] = "none"
                if isinstance(dbinterface.master, BondingInterface):
                    ifdesc["master"] = dbinterface.master.name
                elif isinstance(dbinterface.master, BridgeInterface):
                    ifdesc["bridge"] = dbinterface.master.name
                else:
                    raise InternalError("Unexpected master interface type: "
                                        "{0}".format(dbinterface.master))
            else:
                if dbinterface.assignments:
                    # TODO: Let the templates select from "static"/"dhcp"
                    ifdesc["bootproto"] = "static"
                else:
                    # Don't try to bring up the interface if there are no
                    # addresses assigned to it
                    ifdesc["bootproto"] = "none"

            if isinstance(dbinterface, VlanInterface):
                ifdesc["vlan"] = True
                ifdesc["physdev"] = dbinterface.parent.name

            for addr in dbinterface.assignments:
                if addr.usage == "zebra":
                    if addr.label not in vips:
                        vips[addr.label] = {"ip": addr.ip,
                                            "interfaces": [dbinterface.name]}
                        if addr.dns_records:
                            vips[addr.label]["fqdn"] = addr.dns_records[0]
                    else:
                        # Sanity check
                        if vips[addr.label]["ip"] != addr.ip:
                            raise ArgumentError("Zebra configuration mismatch: "
                                                "label %s has IP %s on "
                                                "interface %s, but IP %s on "
                                                "interface %s." %
                                                (addr.label, addr.ip,
                                                 dbinterface.name,
                                                 vips[addr.label]["ip"],
                                                 vips[addr.label]["interfaces"][0].name))
                        vips[addr.label]["interfaces"].append(dbinterface.name)

                    if dbinterface.name not in transit_interfaces:
                        transit_interfaces.append(dbinterface.name)

                    continue
                elif addr.usage != "system":
                    continue

                net = addr.network

                if addr.label == "":
                    if net.routers:
                        gateway = select_router(self.dbhost.machine, net.routers)
                    else:
                        # Fudge the gateway as the first available ip
                        gateway = net.network[1]
                    if not default_gateway and dbinterface.bootable:
                        default_gateway = gateway

                    ifdesc["ip"] = addr.ip
                    ifdesc["netmask"] = net.netmask
                    ifdesc["broadcast"] = net.broadcast
                    ifdesc["gateway"] = gateway
                    if addr.dns_records:
                        ifdesc["fqdn"] = addr.dns_records[0]
                else:
                    aliasdesc = {"ip": addr.ip,
                                 "netmask": net.netmask,
                                 "broadcast": net.broadcast}
                    if addr.dns_records:
                        aliasdesc["fqdn"] = addr.dns_records[0]
                    if "aliases" in ifdesc:
                        ifdesc["aliases"][addr.label] = aliasdesc
                    else:
                        ifdesc["aliases"] = {addr.label: aliasdesc}

            interfaces[dbinterface.name] = ifdesc

        # If the host uses Zebra, get the list of routers
        if vips:
            for addr in self.dbhost.machine.all_addresses():
                # Ignore non-transit interfaces
                if addr.interface.name not in transit_interfaces:
                    continue
                # Ignore aliases
                if addr.label != "" or addr.usage != "system":
                    continue

                # Note: addr.network is a @property and its value is not kept
                # persistent. The association proxy only keeps a weak reference
                # on its parent, so addr.network.routers can be garbage
                # collected while iterating router_ips, which makes the
                # association proxy upset. Storing addr.network in a variable
                # creates a reference and fixes the issue.
                net = addr.network

                for router_ip in net.router_ips:
                    if addr.interface.name not in routers:
                        routers[addr.interface.name] = []
                    routers[addr.interface.name].append(router_ip)

        personality_template = "personality/%s/config" % \
                self.dbhost.personality.name
        os_template = self.dbhost.operating_system.cfg_path + '/config'

        services = []
        required_services = set(self.dbhost.archetype.services +
                                self.dbhost.personality.services)

        for si in self.dbhost.services_used:
            required_services.discard(si.service)
            services.append(si.cfg_path + '/client/config')
        if required_services:
            raise IncompleteError("Host %s is missing required services %s." %
                                  (self.name, required_services))

        provides = []
        for si in self.dbhost.services_provided:
            provides.append('%s/server/config' % si.cfg_path)

        # Ensure used/provided services have a stable order
        services.sort()
        provides.sort()

        templates = []
        templates.append("archetype/base")
        templates.append(os_template)
        templates.extend(services)
        templates.extend(provides)
        templates.append(personality_template)
        if self.dbhost.cluster:
            clplenary = PlenaryClusterClient(self.dbhost.cluster)
            templates.append(clplenary.plenary_template)
        elif self.dbhost.archetype.cluster_required:
            raise IncompleteError("Host %s archetype %s requires cluster "
                                  "membership." %
                                  (self.name, self.dbhost.archetype.name))

        templates.append("archetype/final")

        # Okay, here's the real content
        arcdir = self.dbhost.archetype.name
        lines.append("# this is an %s host, so all templates should be sourced from there" % self.dbhost.archetype.name)
        lines.append("variable LOADPATH = %s;" % pan([arcdir]))
        lines.append("")
        lines.append("include { 'pan/units' };")
        pmachine = PlenaryMachineInfo(self.dbhost.machine)
        lines.append("'/hardware' = %s;" %
                     pan(StructureTemplate(pmachine.plenary_template)))
        lines.append("'/system/network/interfaces' = %s;" % pan(interfaces))
        lines.append("'/system/network/primary_ip' = %s;" %
                     pan(self.dbhost.machine.primary_ip))
        if default_gateway:
            lines.append("'/system/network/default_gateway' = %s;" %
                         pan(default_gateway))
        if vips:
            lines.append('"/system/network/vips" = %s;' % pan(vips))
        if routers:
            lines.append('"/system/network/routers" = %s;' % pan(routers))
        lines.append("")
        # XXX: remove!
        # We put in a default function: this will be overridden by the
        # personality with a more suitable value, we just leave this here
        # for paranoia's sake.
        lines.append("'/system/function' = 'grid';")
        lines.append("'/system/build' = %s;" % pan(self.dbhost.status.name))
        if self.dbhost.cluster:
            lines.append("'/system/cluster/name' = %s;" % pan(self.dbhost.cluster.name))
        lines.append("")
        for template in templates:
            lines.append("include { %s };" % pan(template))
        lines.append("")

        return

    def write(self, *args, **kwargs):
        # Don't bother writing plenary files for dummy aurora hardware.
        if self.dbhost.machine.model.machine_type == 'aurora_node':
            return 0
        return Plenary.write(self, *args, **kwargs)


class PlenaryNamespacedHost(PlenaryToplevelHost):
    """
    A plenary template describing a host, namespaced by DNS domain
    """
    def __init__(self, dbhost, logger=LOGGER):
        PlenaryToplevelHost.__init__(self, dbhost, logger=logger)
        self.name = dbhost.fqdn
        self.plenary_core = dbhost.machine.primary_name.fqdn.dns_domain.name
        self.plenary_template = "%(plenary_core)s/%(name)s" % self.__dict__