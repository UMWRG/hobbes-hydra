#!/usr/bin/env python
# -*- coding: utf-8 -*-
# (c) Copyright 2013, 2014, 2015 University of Manchester\
#\
# template_builder is free software: you can redistribute it and/or modify\
# it under the terms of the GNU General Public License as published by\
# the Free Software Foundation, either version 3 of the License, or\
# (at your option) any later version.\
#\
# template_builder is distributed in the hope that it will be useful,\
# but WITHOUT ANY WARRANTY; without even the implied warranty of\
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\
# GNU General Public License for more details.\
# \
# You should have received a copy of the GNU General Public License\
# along with template_builder.  If not, see <http://www.gnu.org/licenses/>\
#

import logging

from lxml import etree

import json

import requests

import os, sys

from HydraLib.PluginLib import xsd_validate


log = logging.getLogger(__name__)

__location__ = os.path.split(sys.argv[0])[0]

class HobbesTemplateBuilder(object):
    #Keeps track of all the timeseries we identify in hobbes nodes so we
    #can set the correct data type in the template.
    timeseries = []
    output = "template.xml"

    def build_template_struct(self):
        """
            Read the file containing the network data and build a template from it.
        """

        net_response = requests.get("http://cwn.casil.ucdavis.edu/network/get") #JSON Network
        #http://cwn.casil.ucdavis.edu/excel/create?prmname=SR_CLE    #XLS

        template_struct = {}

        if net_response.status_code != 200:
            raise Exception("A connection error has occurred with status code: %s"%net_response.status_code)

        json_net = json.loads(net_response.content)

        non_attributes = set(['origins', 'prmname', 'regions', 'terminals', 'description', 'extras', 'type'])

        all_extras = [] # For the moment, an extra is seen as a timeseries, so we want to keep track of them separately

        for node in json_net:

            props = node['properties']

            node_type = props['type']

            extras = []
            if template_struct.get(node_type):
                type_attributes = template_struct[node_type]
            else:
                extras = props.get('extras', {}).keys()

                all_extras.extend(extras)
                
                if len(extras) > 0:
                    type_attributes = extras
                else:
                    type_attributes = []

            #Identify the attributes that can be handled automatically
            attributes = set(props.keys()+extras) - non_attributes

            new_attributes = attributes - set(type_attributes)

            if len(new_attributes) > 0:
                log.info("Extending %s attributes with %s"%(node_type, new_attributes))
                type_attributes.extend(list(new_attributes))
                template_struct[node_type] = type_attributes

        self.timeseries = all_extras

        return template_struct

    def convert(self):

        template_struct = self.build_template_struct()

        template_name = 'HydraPlatform template for Hobbes'

        tree = etree.Element('template_definition')
        tname = etree.SubElement(tree, 'template_name')
        tname.text = template_name

        #Stupid HM section
        layout = etree.SubElement(tree, 'layout')
        item = etree.SubElement(layout, 'item')
        name = etree.SubElement(item, 'name')
        name.text = 'grouping'
        value = etree.SubElement(item, 'value')
        
        name2 = etree.SubElement(value, 'name')
        name2.text = template_name

        description = etree.SubElement(value, 'description')
        description.text = "An automatically generated template from the HOBBES network server."

        cats = etree.SubElement(value, 'categories')
        cat  = etree.SubElement(cats, 'category')
        catname  = etree.SubElement(cat, 'name')
        catname.text = 'Resources'
        catdesc  = etree.SubElement(cat, 'description')
        catdesc.text = 'Network Resources'
        catdispname  = etree.SubElement(cat, 'displayname')
        catdispname.text = 'Network Resources'

        groups = etree.SubElement(cat, 'groups')

        for type_name in template_struct:
            grp = etree.SubElement(groups, 'group')
            grpname  = etree.SubElement(grp, 'name')
            grpname.text = type_name
            grpdesc  = etree.SubElement(grp, 'description')
            grpdesc.text = type_name
            grpdispname  = etree.SubElement(grp, 'displayname')
            grpdispname.text = type_name
            grpdispname  = etree.SubElement(grp, 'image')
            grpdispname.text = ''

        ress = etree.SubElement(tree, 'resources')

        for type_name in template_struct:
            res = etree.SubElement(ress, 'resource')
            typ = etree.SubElement(res, 'type')
            typ.text = 'NODE'

            name = etree.SubElement(res, 'name')
            name.text = type_name

            for a in template_struct[type_name]:
                att = etree.SubElement(res, 'attribute')
                att_name = etree.SubElement(att, 'name')
                att_name.text = a
                att_dim = etree.SubElement(att, 'dimension')
                att_dim.text = 'dimensionless'
                att_var = etree.SubElement(att, 'is_var')
                att_var.text = 'N'

        with open(self.output, "w") as fout:
            fout.write(etree.tostring(tree, pretty_print=True))

        xsd_validate(self.output)

def run():
    template_builder = HobbesTemplateBuilder()
    template_builder.convert()
    

if __name__ == '__main__':
    run()

