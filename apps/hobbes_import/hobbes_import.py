#!/usr/bin/env python
# -*- coding: utf-8 -*-
# (c) Copyright 2013, 2014, 2015 University of Manchester\
#\
# ImportJSON is free software: you can redistribute it and/or modify\
# it under the terms of the GNU General Public License as published by\
# the Free Software Foundation, either version 3 of the License, or\
# (at your option) any later version.\
#\
# ImportJSON is distributed in the hope that it will be useful,\
# but WITHOUT ANY WARRANTY; without even the implied warranty of\
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\
# GNU General Public License for more details.\
# \
# You should have received a copy of the GNU General Public License\
# along with ImportJSON.  If not, see <http://www.gnu.org/licenses/>\
#

"""
This plugin imports data directly from Hobbes to Hydra, avoiding the intermediary step of
downloading excel files.

Basics
~~~~~~

The plug-in for exporting a network to a JSON file.
Basic usage::

       ImportJSON.py [-h] [-t NETWORK]

Options
~~~~~~~

====================== ====== ============ =========================================
Option                 Short  Parameter    Description
====================== ====== ============ =========================================
``--help``             ``-h``              Show help message and exit.
``--project-id``       ``-p`` PROJECT_ID   The Project to import data into.
``--node``             ``-n`` NODE_NAME    The name of the node to import data from.
``--target-node``      ``-n`` TARGET_NODE  The ID of the node to import data to.
``--attribute``        ``-a`` ATTRIBUTE_ID The ID of the attribute to import data to.
``--server-url``       ``-u`` SERVER-URL   Url of the server the plugin will
                                           connect to.
                                           Defaults to localhost.
``--session-id``       ``-c`` SESSION-ID   Session ID used by the calling software.
                                           If left empty, the plugin will attempt
                                           to log in itself.
====================== ====== ============ =========================================

"""

import argparse as ap
import logging

from HydraLib import PluginLib
from HydraLib.PluginLib import JsonConnection
from HydraLib.HydraException import HydraPluginError
from HydraLib.PluginLib import write_progress, write_output, validate_plugin_xml, RequestError

from create_hobbes_template import HobbesTemplateBuilder 

import json

import requests

import os, sys

from datetime import datetime

log = logging.getLogger(__name__)

__location__ = os.path.split(sys.argv[0])[0]

class HobbesImporter(object):
    """
       Importer of JSON files into Hydra. Also accepts XML files.
    """
    def __init__(self, url=None, session_id=None):

        self.warnings = []
        self.files    = []
        self.template = None
        self.attributes = []
        self.attr_name_map = {}

        self.nodes = {}
        self.links = {}
        self.groups = {}
        
        self.node_id  = PluginLib.temp_ids()
        self.link_id  = PluginLib.temp_ids()
        self.group_id  = PluginLib.temp_ids()

        self.connection = JsonConnection(url)
        if session_id is not None:
            write_output("Using existing session %s"% session_id)
            self.connection.session_id=session_id
        else:
            self.connection.login()

        #3 steps: start, read, save 
        self.num_steps = 3

    def fetch_project(self, project_id):
        """
            If a project ID is not specified, a new one
            must be created to hold the incoming network. 
            If an ID is specified, we must retrieve the project to make sure
            it exists. If it does not exist, then throw an error.

            Returns the project object so that the network can access it's ID.
        """
        if project_id is not None:
            try:
                project = self.connection.call('get_project', {'project_id':project_id})
                log.info('Loading existing project (ID=%s)' % project_id)
                return project
            except RequestError:
                raise HydraPluginError("Project with ID %s not found"%project_id)

        #Using 'datetime.now()' in the name guarantees a unique project name.
        new_project = dict(
            name = "Hobbes Project created at %s" % (datetime.now()),
            description = \
            "Default project created by the %s plug-in." % \
                (self.__class__.__name__),
        )

        saved_project = self.connection.call('add_project', {'project':new_project})
        
        return saved_project 

    def make_repo_dataset(self, json_repo):
        dataset = {
            'dimension': 'dimensionless',
            'unit':None,
            'data_type': 'descriptor',
            'value'    : json_repo['tag'],
            'metadata' : json_repo,
        }
        return dataset

    def upload_template(self):
        """
            Upload the template file found in ./template.xml
        """
        file_ = os.path.join(__location__, 'template.xml')

        with open(file_) as f:
            xml_template = f.read()

        self.template = self.connection.call('upload_template_xml',
                                    {'template_xml':xml_template})

        self.attributes = self.connection.call('get_template_attributes',
                                               {'template_id':self.template.id})

        #Build a lookup dict of attributes by name
        for a in self.attributes:
            self.attr_name_map[a.name] = a

    def import_network(self, project_id=None):
        """
            Read the file containing the network data and send it to
            the server.
        """
        
        write_output("Fetching Network") 
        write_progress(2, self.num_steps)


        hydra_network = {
            'nodes': [],
            'links': [],
            'groups': [],
            'scenarios': []
        }

        net_response = requests.get("http://cwn.casil.ucdavis.edu/network/get") #JSON Network
        #http://cwn.casil.ucdavis.edu/excel/create?prmname=SR_CLE    #XLS

        if net_response.status_code != 200:
            raise HydraPluginError("A connection error has occurred with status code: %s"%net_response.status_code)

        json_net = json.loads(net_response.content)

        extra_data = {}
        for node in json_net:
            props = node['properties']
            node_coords = node['geometry']['coordinates']
            
            tmp_node_id = self.node_id.next()
            
            node = dict(
                id = tmp_node_id,
                name = props['prmname'],
                x = node_coords[0], #swap these if they are lat-long, not x-y
                y = node_coords[1],
                description = props['description'],
            )
            self.nodes[props['prmname']] = node

            inlinks = [o['link_prmname'] for o in props['origins']]
            for linkname in inlinks:
                if linkname not in self.links:
                    link = dict(
                        id=self.link_id.next(),
                        node_2_id = tmp_node_id,
                        attributes = [],
                        description = "",
                    )
                    self.links[linkname] = link
                else:
                    link = self.links[linkname]
                    link['node_2_id'] = tmp_node_id


            outlinks = [o['link_prmname'] for o in props['terminals']] 
            for linkname in outlinks:
                if linkname not in self.links:
                    link = dict(
                        id=self.link_id.next(),
                        node_1_id = tmp_node_id,
                        attributes = [],
                        description = "",
                    )
                    self.links[linkname] = link
                else:
                    link = self.links[linkname]
                    link['node_1_id'] = tmp_node_id

            import pudb; pudb.set_trace()

            node_groups = props['regions']

            #List of parameters to ignore

            #repo is a special case
            repo = make_repo_dataset(props['repo'])

            extras = props.get('extras', [])
            if extras is not None and len(extras) > 0:
                attr_response = requests.get("http://cwn.casil.ucdavis.edu/network/extras?prmname=%s"%props['prmname']) #JSON attributes
                if attr_response.status_code != 200:
                    raise HydraPluginError("A connection error has occurred with status code: %s"%net_response.status_code)
                extra_data[node_name] = attr_response.content

        project = self.fetch_project(project_id)
        project_id = project.id

        write_output("Saving Network") 
        write_progress(3, self.num_steps) 

        #The network ID can be specified to get the network...
        network = self.connection.call('add_network', {'net':network_data})
        return network

def commandline_parser():
    parser = ap.ArgumentParser(
        description="""Import a network from HOBBES format.

Written by Stephen Knox <stephen.knox@manchester.ac.uk>
(c) Copyright 2015, University of Manchester.
        """, epilog="For more information visit www.hydraplatform.org",
        formatter_class=ap.RawDescriptionHelpFormatter)
    parser.add_argument('-p', '--project-id',
                        help='''The Project to import data into. If none is provided, a new project is created.''')
    parser.add_argument('-u', '--server-url',
                        help='''Specify the URL of the server to which this
                        plug-in connects.''')
    parser.add_argument('-c', '--session_id',
                        help='''Session ID. If this does not exist, a login will be
                        attempted based on details in config.''')
    return parser


def run():

    parser = commandline_parser()
    args = parser.parse_args()
    hobbes_importer = HobbesImporter(url=args.server_url, session_id=args.session_id)



    scenarios = []
    errors = []
    network_id = None
    try:      
        write_progress(1, hobbes_importer.num_steps) 
        
        validate_plugin_xml(os.path.join(__location__, 'plugin.xml'))

        tmpl = HobbesTemplateBuilder()
        tmpl.convert()

        hobbes_importer.upload_template()
        
        net = hobbes_importer.import_network(args.project_id)

        #scenarios = [s.id for s in net.scenarios]
        #network_id = net.id
        message = "Import complete"
    except HydraPluginError as e:
        message="An error has occurred"
        errors = [e.message]
        log.exception(e)
    except Exception, e:
        message="An unknown error has occurred"
        log.exception(e)
        errors = [e]

    xml_response = PluginLib.create_xml_response('ImportJSON',
                                                 network_id,
                                                 scenarios,
                                                 errors,
                                                 hobbes_importer.warnings,
                                                 message,
                                                 hobbes_importer.files)
    print xml_response

if __name__ == '__main__':
    run()

