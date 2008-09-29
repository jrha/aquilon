#!/ms/dist/python/PROJ/core/2.5.2-1/bin/python
""" to refresh network data from dsdb """

import os
import sys
import logging
import optparse

DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.realpath(os.path.join(DIR, '..', '..', '..')))
import aquilon.aqdb.depends

from sqlalchemy.exceptions      import DatabaseError, IntegrityError

#TODO: fix all the damn location imports with a shortcut in loc/__init__
from aquilon.aqdb.loc.hub       import Hub
from aquilon.aqdb.loc.city      import City
from aquilon.aqdb.loc.company   import Company
from aquilon.aqdb.loc.country   import Country
from aquilon.aqdb.loc.building  import Building
from aquilon.aqdb.loc.continent import Continent
from aquilon.aqdb.loc.location  import Location

#TODO: likewise, all the imports for system subtypes
from aquilon.aqdb.sy.system     import System
from aquilon.aqdb.sy.tor_switch import TorSwitch

from aquilon.aqdb.db_factory    import db_factory
from aquilon.aqdb.utils.report  import RefreshReport
from aquilon.aqdb.dsdb          import DsdbConnection
from aquilon.aqdb.net.network   import Network, _mask_to_cidr, get_bcast

from aquilon.aqdb.utils.shutils import ipshell

class NetRecord(object):
    """ might be a handy gizmo for comparing networks """
    #TODO: USE KW FOR > 3 arguments, buddy
    def __init__(self, ip, name, net_type, mask, bldg, side, dsdb_id, comments=None,
                 *args, **kw):
        #TODO: add comment updating in later, too much noise for now
        self.ip       = ip
        self.name     = name
        self.net_type = net_type
        self.mask     = mask
        self.bldg     = bldg
        self.side     = side
        self.dsdb_id  = dsdb_id
        if comments:
            self.comments = comments

    def __eq__(self, other):
        if type(other) != Network:
            raise TypeError(
                         'type of %s is %s, should be Network'%(aq,type(aq)))

        if (self.name.lower() == other.name and
            self.net_type     == other.network_type and
            self.mask         == other.mask and
            self.bldg         == other.location.name and
            self.side         == other.side): #and
            #self.comments == other.comments):
            return True
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def update_aq_net(self, aq, log, report):
        if type(aq) != Network:
            #TODO: make sure you're caught
            raise TypeError(
                         'diff_aq_net%s is %s, should be Network'%(aq,type(aq)))
        if self.ip != aq.ip:
            m = 'update_aq_net: network ip mismatch (dsdb)%s != %s(aqdb)'%(
                                                                self.ip, aq.ip)
            raise ValueError(m)

        if self.bldg != aq.location.name:
            m = 'update_aq_net: location name mismatch (dsdb)%s != %s(aqdb)'%s(
                                                    self.bldg, aq.location.name)
            raise ValueError(m)
        msg = ''
        if self.bldg != aq.location.name:
            msg += 'updating network %s to name %s\n'%(aq, self.name)
            report.upds.append(msg)
            log.debug(msg)

        if self.name.lower() != aq.name:
            msg += 'updating network %s to name %s'%(aq, self.name)
            log.debug(msg)
            report.upds.append(msg)
            aq.name = self.name

        if self.net_type != aq.network_type:
            msg = 'updating network %s to type %s'%(aq, self.net_type)
            log.debug(msg)
            report.upds.append(msg)
            aq.network_type = self.net_type

        if self.mask != aq.mask:
            #BUG: you must update bcast here!
            msg = 'updating network %s with mask %s'%(aq, self.mask)
            log.debug(msg)
            report.upds.append(msg)
            aq.mask = self.mask

        if self.side != aq.side:
            msg = 'updating network %s to name %s'%(aq, self.name)
            log.debug(msg)
            report.upds.append(msg)
            aq.side = self.side

        return aq

    def __repr__(self):
        return '<Network %s ip=%s, type=%s, mask=%s, bldg=%s, side=%s>'%(
                self.name, self.ip, self.net_type, self.mask,
                self.bldg, self.side)

class NetRefresher(object):
    """ guess what I do?"""
    #do Borg later on?

    #Dependency injection: allows us to supply our own *fake* dsdb connection
    def __init__(self, dsdb_cnxn, *args, **kw):
        #TODO: singleton, accept args for logger level

        #if not getattr(self, 'dsdb', None):
        self.dsdb = dsdb_cnxn
        assert self.dsdb

        #if not getattr(self, 'aqdb', None):
        self.aqdb = db_factory()
        assert self.aqdb

        q = self.aqdb.s.query(Building)
        self.location = q.filter_by(name=opts.building_name).one()
        assert type(self.location) is Building

        #if not getattr(self, 'report', None):
        self.report = RefreshReport()
        assert self.report

        if not getattr(self, 'log', None):
            self.log = logging.getLogger('net_refresh')
            assert self.log

            if opts.verbose > 1:
                log_level = logging.DEBUG
            elif opts.verbose > 0:
                log_level = logging.INFO
            else:
                log_level = logging.WARN

            #TODO: call this in main
            logging.basicConfig(level=log_level,
                            format='%(asctime)s %(levelname)-6s %(message)s',
                            datefmt='%a, %d %b %Y %H:%M:%S')

    def _pull_dsdb_data(self, *args, **kw):
        """ loc argument is a sysloc string (DSDB stores this instead) """
        d = {}
        #query returns in order name, ip, mask, type_id, bldg, side
        for (name, ip, mask, type, bldg, side, dsdb_id) in \
                        self.dsdb.get_network_by_sysloc(self.location.sysloc()):
            d[ip] = NetRecord(ip, name, type, mask, bldg, side, dsdb_id)
        return d

    def _pull_aqdb_data(self, *args, **kw):
        """ loc argument is a BUILDING CODE, different from dsdb """
        d = {}

        q = self.aqdb.s.query(Network)
        for n in q.filter_by(location=self.location).all():
            d[n.ip] = n
        return d

    def _rollback(self, msg):
        """ a DRY method for error handling """
        self.log.error(msg)
        self.report.errs.append(msg)
        self.aqdb.s.rollback()

    def refresh(self, *args, **kw):
        """ compares and refreshes the network table from dsdb to aqdb using
            sets makes computing union and delta of keys simple and succinct """

        ds = self._pull_dsdb_data(*args, **kw)
        dset = set(ds.keys())

        aq = self._pull_aqdb_data(*args, **kw)
        aset = set(aq.keys())

        deletes  = aset - dset
        if deletes:
            self._do_deletes(deletes, aq, *args, **kw)
            aq = self._pull_aqdb_data(*args, **kw)
            aset = set(aq.keys())

        adds = dset - aset
        if adds:
            self._do_adds(adds, ds, *args, **kw)
            aq = self._pull_aqdb_data(*args, **kw)
            aset = set(aq.keys())

        compares = aset & dset
        if compares:
            self._do_updates(aset & dset , aq, ds, *args, **kw)

    def _do_deletes(self, k, aq, *args, **kw):
        """ Deletes networks in aqdb and not in dsdb. It logs and handles
            associated reporting messages.

            arguments: list of keys and dict of aqdb networks to delete
            returns:   True/False on total success/a single failure """
            #TODO: revisit this ^^^
        for i in k:
            self.log.debug('deleting %s'%(aq[i]))
            self.report.dels.append(aq[i])

            if opts.commit:
                try:
                    self.aqdb.s.delete(aq[i])
                    self.aqdb.s.commit()
                    self.aqdb.s.flush()
                except IntegrityError,e:
#                    """ TODO: get records that connects back to the network and
#                            do something about it: delete it, or send message.
#                            enhancement: start marking objects for deletion and
#                            delete them after a week or two of no activity """
                    print e
                    ipshell()
                except Exception, e:
                    self._rollback(e)
                    continue

    def _do_adds(self, k, ds, *args, **kw):
        """ Adds networks in dsdb and not in aqdb. Handles the logging and
            job reporting along the way.

            arguments: list of keys (ip addresses) and dsdb NetRecords

            returns:   # of networks added or False based on total success or
                       a single failure """ #TODO: revisit this
        for i in k:
            try:
                c = _mask_to_cidr[ds[i].mask]
                net = Network(name         = ds[i].name,
                              ip           = ds[i].ip,
                              mask         = ds[i].mask,
                              cidr         = c,
                              bcast        = get_bcast(ds[i].ip, c),
                              network_type = ds[i].net_type,
                              side         = ds[i].side,
                              location     = self.location,
                              dsdb_id      = ds[i].dsdb_id)
                net.comments = getattr(ds[i], 'comments', None)
    #TODO: use a memoized query:
    #self.aqdb.s.query(Building).filter_by(name=ds[i].bldg).one()
            except Exception, e:
                self.report.errs.append(e)
                self.log.error(e)
                continue

            #log here to get more detailed/uniform output
            self.log.debug('adding %s'%(net))
            self.report.adds.append(net)

            if opts.commit:
                self.report.adds.append(net)
                try:
                    self.aqdb.s.add(net)
                    self.aqdb.s.commit()
                    self.aqdb.s.flush()
                except Exception, e:
                    self._rollback(e)

    def _do_updates(self, k, aq, ds, *args, **kw):
        """ Makes changes to networks which have differences, logs/reports. We
            do this *VERY* cautiously with seperate try/except for everything

            arguments: list of keys (ip addresses) for networks present in both
                       data sources, plus a hash of the relevent data to compare

            returns:   # of networks successfully updated or False if there's a
                       single failure  """
        for i in k:
            if ds[i] != aq[i]:
                #get an updated version of the aqdb network
                print ds[i]
                print '    %s'%(aq[i])
                try:
                    aq[i] = ds[i].update_aq_net(aq[i], self.log, self.report)
                except ValueError, e:
                    self.report.errs.append(e)
                    self.log.error(e)

                if opts.commit:
                    try:
                        self.log.debug('trying to commit the update\n')
                        self.aqdb.s.update(aq[i])
                        self.aqdb.s.commit()
                        self.aqdb.s.flush()
                        self.report.upds.append(ds[i].name)
                    except Exception, e:
                        self._rollback(e)

def main(*args, **kw):
    usage = """ usage: %prog [options]
    refreshes location data from dsdb to aqdb """

    desc = 'Synchronizes networks from DSDB to AQDB'

    p = optparse.OptionParser(usage=usage, prog=sys.argv[0], version='0.1',
                              description=desc)

    p.add_option('-v',
                 action = 'count',
                 dest   = 'verbose',
                 help   = 'increase verbosity by adding more (vv), etc.')

    p.add_option('-b', '--building',
                 action = 'store',
                 dest   = 'building_name',
                 default = 'dd' )

    p.add_option('-e', '--exec',
                      action  = 'store_true',
                      dest    = 'commit',
                      default = False,
                      help    = 'commit changes (default = False for tests)')
    global opts
    opts, args = p.parse_args()

    dsdb = DsdbConnection()

    nr = NetRefresher(dsdb)
    nr.refresh()

    if opts.verbose < 2:
        #really verbose runs don't need reporting
        nr.report.display()


if __name__ == '__main__':
    main(sys.argv)
