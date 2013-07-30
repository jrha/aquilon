# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2012,2013  Contributor
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

from operator import attrgetter
import logging

from aquilon.aqdb.model import MetaCluster
from aquilon.worker.templates import (Plenary, ObjectPlenary, StructurePlenary,
                                      PlenaryCollection, PlenaryPersonalityBase,
                                      PlenaryResource,
                                      PlenaryServiceInstanceClientDefault)
from aquilon.worker.templates.panutils import (StructureTemplate, PanValue,
                                               pan_assign, pan_include,
                                               pan_append)
from aquilon.worker.locks import CompileKey


LOGGER = logging.getLogger(__name__)


class PlenaryMetaCluster(PlenaryCollection):
    """
    A facade for the variety of PlenaryMetaCluster subsidiary files
    """
    def __init__(self, dbcluster, logger=LOGGER):
        super(PlenaryMetaCluster, self).__init__(logger=logger)

        self.dbobj = dbcluster
        self.plenaries.append(PlenaryMetaClusterObject(dbcluster, logger=logger))
        self.plenaries.append(PlenaryMetaClusterData(dbcluster, logger=logger))


class PlenaryMetaClusterData(StructurePlenary):

    @classmethod
    def template_name(cls, dbmetacluster):
        return "clusterdata/" + dbmetacluster.name

    def __init__(self, dbmetacluster, logger=LOGGER):
        super(PlenaryMetaClusterData, self).__init__(dbmetacluster,
                                                     logger=logger)

        self.name = dbmetacluster.name

        # TODO maybe metaclusterdata
        self.plenary_core = "clusterdata"
        self.plenary_template = dbmetacluster.name

    def get_key(self):
        return CompileKey(domain=self.dbobj.branch.name,
                          profile=self.plenary_template, logger=self.logger)

    def body(self, lines):
        pan_assign(lines, "system/metacluster/name", self.name)
        pan_assign(lines, "system/metacluster/type", self.dbobj.cluster_type)

        dbloc = self.dbobj.location_constraint
        pan_assign(lines, "system/metacluster/sysloc/location", dbloc.sysloc())
        if dbloc.continent:
            pan_assign(lines, "system/metacluster/sysloc/continent",
                       dbloc.continent.name)
        if dbloc.city:
            pan_assign(lines, "system/metacluster/sysloc/city", dbloc.city.name)
        if dbloc.campus:
            pan_assign(lines, "system/metacluster/sysloc/campus",
                       dbloc.campus.name)
            ## maintaining this so templates dont break
            ## during transtion period.. should be DEPRECATED
            pan_assign(lines, "system/metacluster/campus", dbloc.campus.name)
        if dbloc.building:
            pan_assign(lines, "system/metacluster/sysloc/building",
                       dbloc.building.name)
        if dbloc.room:
            pan_assign(lines, "system/cluster/rack/room", dbloc.room)
        if dbloc.bunker:
            pan_assign(lines, "system/cluster/sysloc/bunker", dbloc.bunker.name)
        if dbloc.rack:
            pan_assign(lines, "system/metacluster/rack/row",
                       dbloc.rack.rack_row)
            pan_assign(lines, "system/metacluster/rack/column",
                       dbloc.rack.rack_column)
            pan_assign(lines, "system/metacluster/rack/name",
                       dbloc.rack.name)

        lines.append("")

        pan_assign(lines, "system/metacluster/members",
                   [member.name for member in self.dbobj.members])

        lines.append("")

        pan_assign(lines, "system/build", self.dbobj.status.name)

        lines.append("")
        if self.dbobj.resholder:
            for resource in sorted(self.dbobj.resholder.resources,
                                   key=attrgetter('resource_type', 'name')):
                res_path = PlenaryResource.template_name(resource)
                pan_append(lines, "system/resources/" + resource.resource_type,
                           StructureTemplate(res_path))


class PlenaryMetaClusterObject(ObjectPlenary):

    @classmethod
    def template_name(cls, dbmetacluster):
        return "clusters/" + dbmetacluster.name

    def __init__(self, dbmetacluster, logger=LOGGER):
        super(PlenaryMetaClusterObject, self).__init__(dbmetacluster,
                                                       logger=logger)

        self.name = dbmetacluster.name

        self.loadpath = self.dbobj.personality.archetype.name
        self.plenary_core = "clusters"
        self.plenary_template = dbmetacluster.name

    def get_key(self):
        return CompileKey(domain=self.dbobj.branch.name,
                          profile=self.plenary_template, logger=self.logger)

    def body(self, lines):
        pan_include(lines, ["pan/units", "pan/functions"])
        pan_assign(lines, "/",
                   StructureTemplate("clusterdata/%s" % self.name,
                                     {"metadata": PanValue("/metadata")}))
        pan_include(lines, "archetype/base")

        #for esx_management_server
        for servinst in sorted(self.dbobj.service_bindings):
            path = PlenaryServiceInstanceClientDefault.template_name(servinst)
            pan_include(lines, path)

        path = PlenaryPersonalityBase.template_name(self.dbobj.personality)
        pan_include(lines, path)
        pan_include(lines, "archetype/final")


Plenary.handlers[MetaCluster] = PlenaryMetaCluster
