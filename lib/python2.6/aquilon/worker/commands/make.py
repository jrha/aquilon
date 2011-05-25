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
"""Contains the logic for `aq make`."""


from aquilon.exceptions_ import ArgumentError
from aquilon.worker.broker import BrokerCommand
from aquilon.worker.dbwrappers.host import hostname_to_host
from aquilon.aqdb.model import (Archetype, HostLifecycle,
                                OperatingSystem, Personality)
from aquilon.worker.templates.domain import TemplateDomain
from aquilon.worker.locks import lock_queue, CompileKey
from aquilon.worker.services import Chooser


class CommandMake(BrokerCommand):

    required_parameters = ["hostname"]

    def render(self, session, logger, hostname, osname, osversion,
               archetype, personality, buildstatus, keepbindings, os,
               **arguments):
        dbhost = hostname_to_host(session, hostname)

        # Currently, for the Host to be created it *must* be associated with
        # a Machine already.  If that ever changes, need to check here and
        # bail if dbhost.machine does not exist.

        if archetype and archetype != dbhost.archetype.name:
            if not personality:
                raise ArgumentError("Changing archetype also requires "
                                    "specifying --personality.")
        if personality:
            if archetype:
                dbarchetype = Archetype.get_unique(session, archetype,
                                                   compel=True)
            else:
                dbarchetype = dbhost.archetype

            if not os and not osname and not osversion and \
               dbhost.operating_system.archetype != dbarchetype:
                raise ArgumentError("{0} belongs to {1:l}, not {2:l}.  Please "
                                    "specify --osname/--osversion."
                                    .format(dbhost.operating_system,
                                            dbhost.operating_system.archetype,
                                            dbarchetype))

            dbpersonality = Personality.get_unique(session, name=personality,
                                                   archetype=dbarchetype,
                                                   compel=True)
            if dbhost.cluster and \
               dbhost.cluster.personality != dbpersonality:
                raise ArgumentError("Cannot change personality of host {0} "
                                    "while it is a member of "
                                    "{1:l}.".format(dbhost.fqdn, dbhost.cluster))
            dbhost.personality = dbpersonality

        dbos = self.get_os(session, dbhost, osname, osversion, os)
        if dbos:
            # Hmm... no cluster constraint here...
            dbhost.operating_system = dbos

        if buildstatus:
            dbstatus = HostLifecycle.get_unique(session, buildstatus,
                                                compel=True)
            dbhost.status.transition(dbhost, dbstatus)

        session.flush()

        if dbhost.archetype.is_compileable:
            self.compile(session, dbhost, logger, keepbindings)

        return

    def compile(self, session, dbhost, logger, keepbindings):
        chooser = Chooser(dbhost, logger=logger,
                          required_only=not(keepbindings))
        chooser.set_required()
        chooser.flush_changes()

        # Force a host lock as pan might overwrite the profile...
        key = CompileKey.merge([chooser.get_write_key(),
                                CompileKey(domain=dbhost.branch.name,
                                           profile=dbhost.fqdn,
                                           logger=logger)])
        try:
            lock_queue.acquire(key)
            chooser.write_plenary_templates(locked=True)

            td = TemplateDomain(dbhost.branch, dbhost.sandbox_author,
                                logger=logger)
            td.compile(session, only=dbhost.fqdn, locked=True)

        except:
            if chooser:
                chooser.restore_stash()

            # Okay, cleaned up templates, make sure the caller knows
            # we've aborted so that DB can be appropriately rollback'd.
            raise

        finally:
            lock_queue.release(key)

        return

    def get_os(self, session, dbhost, osname, osversion, os):
        """Wrapper for handling deprecated os argument."""
        if os:
            try:
                (splitname, splitversion) = os.split('/')
            except ValueError:
                raise ArgumentError("Incorrect value for --os.  Please use "
                                    "--osname/--osversion instead.")
            if not osname:
                osname = splitname
            if not osversion:
                osversion = splitversion
        if not osname:
            osname = dbhost.operating_system.name
        if osname and osversion:
            return OperatingSystem.get_unique(session, name=osname,
                                              version=osversion,
                                              archetype=dbhost.archetype,
                                              compel=True)
        elif osname != dbhost.operating_system.name:
            raise ArgumentError("Please specify a version to use for OS %s." %
                                osname)
        return None