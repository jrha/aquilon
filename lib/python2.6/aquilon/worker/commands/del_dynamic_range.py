# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
#
# Copyright (C) 2009,2010,2011  Contributor
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


from aquilon.worker.broker import BrokerCommand
from aquilon.aqdb.model import ARecord, NetworkEnvironment
from aquilon.aqdb.model.network import get_net_id_from_ip
from aquilon.exceptions_ import ArgumentError, ProcessException
from aquilon.worker.locks import lock_queue, DeleteKey
from aquilon.worker.processes import DSDBRunner
from aquilon.worker.dbwrappers.dns import delete_dns_record


class CommandDelDynamicRange(BrokerCommand):

    required_parameters = ["startip", "endip"]

    def render(self, session, logger, startip, endip, **arguments):
        key = DeleteKey("system", logger=logger)
        try:
            lock_queue.acquire(key)
            self.del_dynamic_range(session, logger, startip, endip)
            session.commit()
        finally:
            lock_queue.release(key)
        return

    def del_dynamic_range(self, session, logger, startip, endip):
        dbnet_env = NetworkEnvironment.get_unique_or_default(session)
        startnet = get_net_id_from_ip(session, startip, dbnet_env)
        endnet = get_net_id_from_ip(session, endip, dbnet_env)
        if startnet != endnet:
            raise ArgumentError("IP addresses %s (%s) and %s (%s) must be "
                                "on the same subnet." %
                                (startip, startnet.ip, endip, endnet.ip))
        q = session.query(ARecord)
        q = q.filter_by(network=startnet)
        q = q.filter(ARecord.ip >= startip)
        q = q.filter(ARecord.ip <= endip)
        q = q.order_by(ARecord.ip)
        existing = q.all()
        if not existing:
            raise ArgumentError("Nothing found in range.")
        if existing[0].ip != startip:
            raise ArgumentError("No system found with IP address %s." % startip)
        if existing[-1].ip != endip:
            raise ArgumentError("No system found with IP address %s." % endip)
        invalid = [s for s in existing if s.dns_record_type != 'dynamic_stub']
        if invalid:
            raise ArgumentError("The range contains non-dynamic systems:\n" +
                                "\n".join([format(i, "a") for i in invalid]))
        self.del_dynamic_stubs(session, logger, existing)

    def del_dynamic_stubs(self, session, logger, dbstubs):
        stubs = {}
        for stub in dbstubs:
            stubs[stub.fqdn] = dict(ip=stub.ip, label="{0:a}".format(stub))
            delete_dns_record(stub)
        session.flush()

        dsdb_runner = DSDBRunner(logger=logger)
        stubs_removed = {}
        try:
            for (fqdn, info) in stubs.items():
                logger.client_info("Removing %s from DSDB.", info['label'])
                dsdb_runner.delete_host_details(info['ip'])
                stubs_removed[fqdn] = info['ip']
        except ProcessException, e:
            # Try to roll back anything that had succeeded...
            for (fqdn, ip) in stubs_removed.items():
                try:
                    dsdb_runner.add_host_details(fqdn, ip, None, None)
                except ProcessException, pe2:
                    logger.client_info("Failed rolling back DSDB entry for "
                                       "%s with IP Address %s: %s" %
                                       (fqdn, ip, pe2))
            raise e
        return