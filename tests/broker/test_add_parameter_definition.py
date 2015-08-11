#!/usr/bin/env python
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2012,2013,2014,2015  Contributor
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
"""Module for testing parameter definition support."""

if __name__ == "__main__":
    import utils
    utils.import_depends()

import unittest2 as unittest
from broker.brokertest import TestBrokerCommand

default_param_defs = {
    "testdefault": {
        # No explicit type
        "description": "Blah",
    },
    "testrequired": {
        "type": "string",
        "required": True,
    },
    "test_rebuild_required": {
        "type": "string",
        "activation": "rebuild",
    },
    "teststring": {
        "type": "string",
        "default": "default",
    },
    "testint": {
        "type": "int",
        "default": "60",
        "invalid_default": "bad_int",
    },
    "testfloat": {
        "type": "float",
        "default": "100.100",
        "invalid_default": "bad_float",
    },
    "testboolean": {
        "type": "boolean",
        "default": "yes",
        "invalid_default": "bad_boolean",
    },
    "testlist": {
        "type": "list",
        "default": "val1,val2",
    },
    "testjson": {
        "type": "json",
        "default": '{"val1": "val2"}',
        "invalid_default": "bad_json",
    },
}


class TestAddParameterDefinition(TestBrokerCommand):
    def setUp(self):
        super(TestAddParameterDefinition, self).setUp()
        self.proto = self.protocols['aqdsystems_pb2']

        desc = self.proto.Feature.DESCRIPTOR
        self.activation_type = desc.fields_by_name["activation"].enum_type

    def test_100_add_all(self):
        for path, params in default_param_defs.items():
            cmd = ["add_parameter_definition", "--archetype", "aquilon",
                   "--path", path, "--template", "foo"]
            if "type" in params:
                cmd.extend(["--value_type", params["type"]])
            if "default" in params:
                cmd.extend(["--default", params["default"]])
            if params.get("required", False):
                cmd.append("--required")
            if "activation" in params:
                cmd.extend(["--activation", params["activation"]])

            out = self.statustest(cmd)
            if "default" in params:
                self.matchoutput(out, "You need to run 'aq flush --personalities' for "
                                 "the default value to take effect.", cmd)

    def test_105_show_paramdef(self):
        cmd = ["show_parameter_definition", "--archetype", "aquilon",
               "--path", "testrequired"]
        out = self.commandtest(cmd)
        self.searchoutput(out,
                          r'Parameter Definition: testrequired \[required\]\s*'
                          r'Type: string\s*'
                          r'Template: foo\s*'
                          r'Activation: dispatch\s*',
                          cmd)

    def test_120_clean_path(self):
        for path in ["/startslash", "endslash/"]:
            cmd = ["add_parameter_definition", "--archetype", "aquilon",
                   "--path=%s" % path, "--template=foo", "--value_type=string"]
            self.noouttest(cmd)

    def test_130_valid_path(self):
        for path in ["multi/part1/part2", "noslash", "valid/with_under", "valid/with.dot",
                     "valid/with-dash", "with_under", "with.dot", "with-dash"]:

            cmd = ["add_parameter_definition", "--archetype", "aquilon",
                   "--path=%s" % path, "--template=foo", "--value_type=string"]
            self.noouttest(cmd)

            cmd = ["del_parameter_definition", "--archetype", "aquilon",
                   "--path=%s" % path]
            self.noouttest(cmd)

    def test_300_add_existing(self):
        cmd = ["add_parameter_definition", "--archetype", "aquilon",
               "--path=teststring", "--value_type=string", "--description=blaah",
               "--template=foo", "--required", "--default=default"]
        err = self.badrequesttest(cmd)
        self.matchoutput(err,
                         "Parameter Definition teststring, parameter "
                         "definition holder aquilon already exists.",
                         cmd)

    def test_300_invalid_defaults(self):
        for path, params in default_param_defs.items():
            if "invalid_default" not in params:
                continue

            cmd = ["add_parameter_definition", "--archetype", "aquilon",
                   "--path", path, "--value_type", params["type"],
                   "--template", "foo", "--default", params["invalid_default"]]
            out = self.badrequesttest(cmd)
            self.matchoutput(out, "for default for path=%s" % path, cmd)

    def test_300_add_noncompileable_arch(self):
        cmd = ["add_parameter_definition", "--archetype", "windows",
               "--path=testint", "--description=blaah",
               "--template=foo", "--value_type=int", "--default=60"]
        out = self.badrequesttest(cmd)
        self.matchoutput(out, "Archetype windows is not compileable.", cmd)

    def test_300_add_rebuild_default(self):
        cmd = ["add_parameter_definition", "--archetype", "aquilon",
               "--path=test_rebuild_required_default", "--default=default",
               "--template=foo", "--value_type=string", "--activation=rebuild"]
        out = self.unimplementederrortest(cmd)
        self.matchoutput(out, "Setting a default value for a parameter which "
                         "requires rebuild would cause all existing hosts to "
                         "require a rebuild, which is not supported.", cmd)

    def test_300_update_rebuild_required_default(self):
        cmd = ["update_parameter_definition", "--archetype", "aquilon",
               "--path=test_rebuild_required", "--default=default"]
        out = self.unimplementederrortest(cmd)
        self.matchoutput(out, "Changing the default value of a parameter "
                         "which requires rebuild would cause all existing "
                         "hosts to require a rebuild, which is not supported.",
                         cmd)

    def test_300_invalid_path(self):
        for path in ["!badchar", "@badchar", "#badchar", "$badchar", "%badchar", "^badchar",
                     "&badchar", "*badchar" ":badchar", ";badcharjk", "+badchar"]:
            cmd = ["add_parameter_definition", "--archetype", "aquilon",
                   "--path=%s" % path, "--template=foo", "--value_type=string"]
            err = self.badrequesttest(cmd)
            self.matchoutput(err, "Invalid path %s specified, path cannot start with special characters" % path,
                             cmd)

    def test_300_show_bad_path(self):
        cmd = ["show_parameter_definition", "--archetype", "aquilon",
               "--path", "path-does-not-exist"]
        out = self.notfoundtest(cmd)
        self.matchoutput(out, "Parameter Definition path-does-not-exist, "
                         "parameter definition holder aquilon not found.", cmd)

    def test_300_show_archetype_no_params(self):
        cmd = ["show_parameter_definition", "--archetype", "windows",
               "--path", "path-does-not-exist"]
        out = self.notfoundtest(cmd)
        self.matchoutput(out, "Archetype windows does not have parameters.", cmd)

    def test_400_verify_all(self):
        cmd = ["search_parameter_definition", "--archetype", "aquilon"]

        out = self.commandtest(cmd)
        for path, params in default_param_defs.items():
            pattern = "Parameter Definition: " + path
            if params.get("required", False):
                pattern += r' \[required\]'
            pattern += r"\s*"
            if "type" in params:
                pattern += "Type: " + params["type"] + r"\s*"
            else:
                pattern += r"Type: string\s*"
            pattern += r"Template: foo\s*"
            if "default" in params:
                pattern += "Default: " + params["default"] + r"\s*"
            if "activation" in params:
                pattern += "Activation: " + params["activation"] + r"\s*"
            else:
                pattern += r"Activation: dispatch\s*"

            self.searchoutput(out, pattern, cmd)

        self.searchoutput(out, r'Parameter Definition: startslash\s*', cmd)
        self.searchoutput(out, r'Parameter Definition: endslash\s*', cmd)

    def test_400_verify_all_proto(self):
        cmd = ["search_parameter_definition", "--archetype", "aquilon", "--format=proto"]
        result = self.protobuftest(cmd, expect=11)[:]
        param_defs = dict((param_def.path, param_def) for param_def in result)

        self.assertIn('endslash', param_defs)
        self.assertEqual(param_defs['endslash'].value_type, 'string')
        self.assertIn('startslash', param_defs)
        self.assertEqual(param_defs['startslash'].value_type, 'string')

        for path, params in default_param_defs.items():
            self.assertIn(path, param_defs)
            self.assertEqual(param_defs[path].template, "foo")
            if "type" in params:
                self.assertEqual(param_defs[path].value_type, params["type"])
            else:
                self.assertEqual(param_defs[path].value_type, "string")
            if "default" in params:
                self.assertEqual(param_defs[path].default, params["default"])
            else:
                self.assertEqual(param_defs[path].default, "")
            self.assertEqual(param_defs[path].is_required,
                             params.get("required", False))
            if "activation" in params:
                val = self.activation_type.values_by_name[params["activation"].upper()]
                self.assertEqual(param_defs[path].activation, val.number)
            else:
                self.assertEqual(param_defs[path].activation, self.proto.DISPATCH)

    def test_500_update(self):
        cmd = ["update_parameter_definition", "--archetype", "aquilon",
               "--path=testint", "--description=testint",
               "--default=100", "--required", "--activation", "reboot"]
        out = self.statustest(cmd)
        self.matchoutput(out, "You need to run 'aq flush --personalities' for "
                         "the change of the default value to take effect.", cmd)

    def test_510_verify_update(self):
        cmd = ["search_parameter_definition", "--archetype", "aquilon"]
        out = self.commandtest(cmd)
        self.searchoutput(out,
                          r'Parameter Definition: testint \[required\]\s*'
                          r'Type: int\s*'
                          r'Template: foo\s*'
                          r'Default: 100\s*'
                          r'Activation: reboot\s*'
                          r'Description: testint\s*',
                          cmd)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAddParameterDefinition)
    unittest.TextTestRunner(verbosity=2).run(suite)