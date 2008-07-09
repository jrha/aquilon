#!/ms/dist/python/PROJ/core/2.5.0/bin/python
# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# $Header$
# $Change$
# $DateTime$
# $Author$
# Copyright (C) 2008 Morgan Stanley
#
# This module is part of Aquilon
"""Module for testing the add model command."""

import os
import sys
import unittest

if __name__ == "__main__":
    BINDIR = os.path.dirname(os.path.realpath(sys.argv[0]))
    SRCDIR = os.path.join(BINDIR, "..", "..")
    sys.path.append(os.path.join(SRCDIR, "lib", "python2.5"))

from brokertest import TestBrokerCommand


class TestAddModel(TestBrokerCommand):

    def testadduttorswitch(self):
        command = "add model --name uttorswitch --vendor hp --type tor_switch --cputype xeon_2500 --cpunum 1 --mem 8192 --disktype scsi --disksize 36 --nics 4"
        self.noouttest(command.split(" "))

    def testverifyadduttorswitch(self):
        command = "show model --name uttorswitch"
        out = self.commandtest(command.split(" "))
        self.matchoutput(out, "Model: hp uttorswitch", command)
        self.matchoutput(out, "MachineSpecs for hp uttorswitch", command)
        self.matchoutput(out, "Cpu: xeon_2500 x 1", command)
        self.matchoutput(out, "Memory: 8192 MB", command)
        self.matchoutput(out, "NIC count: 4", command)
        self.matchoutput(out, "Disk: 36 GB scsi", command)


if __name__=='__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAddModel)
    unittest.TextTestRunner(verbosity=2).run(suite)

