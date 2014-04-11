# Copyright (C) 2012 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

import json
import urllib
import ast
from webob import Response
#import sys   

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller import dpset
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0
import ofctl_v6
#from ryu.lib import ofctl_v1_0
from ryu.app.wsgi import ControllerBase, WSGIApplication


LOG = logging.getLogger('ryu.app.ofctl_rest_v6')

# REST API
#
## Retrieve the switch stats
#
# get the list of all switches
# GET /stats/switches
#
# get the desc stats of the switch
# GET /stats/desc/<dpid>
#
# get flows stats of the switch
# GET /stats/flow/<dpid>
#
# get ports stats of the switch
# GET /stats/port/<dpid>
#
## Update the switch stats
#
# add a flow entry
# POST /stats/flowentry/add
#
# modify all matching flow entries
# POST /stats/flowentry/modify
#
# delete all matching flow entries
# POST /stats/flowentry/delete
#
# delete all flow entries of the switch
# DELETE /stats/flowentry/clear/<dpid>
#


class StatsController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(StatsController, self).__init__(req, link, data, **config)
        self.dpset = data['dpset']
        self.waiters = data['waiters']

    def get_homepage(self, req, **_kwargs):

         return (Response(content_type='text/html', 
            body='<a href="/stats/switches">get the list of all switches</a><br/>'))

    def get_dpids(self, req, **_kwargs):
        dps = self.dpset.dps.keys()

        body = json.dumps(dps)
        return (Response(content_type='application/json', body=body))
        """
        if (dps == None):
            return (Response(content_type="text/html", body=None))
            
        body = ''
        for dp in dps:

            body = 'Switch '+str(dp)+'<br/>'
            href = '/stats/desc/'+str(dp)
            body += '<a href='+href+'>'+'get the desc stats of the switch '+str(dp)+'</a><br/>'
            href = '/stats/flow/'+str(dp)
            body += '<a href='+href+'>'+'get flows stats of the switch '+str(dp)+'</a><br/>'
            href = '/stats/port/'+str(dp)
            body += '<a href='+href+'>'+'get ports stats of the switch '+str(dp)+'</a><br/>'

            form1 ='<form name="form1" action="/stats/flowentry/add" method="POST" target="_self">'
            form1 +=' add a flow entry: <input type="text" name="text1" size="24"> <input type="submit" name="Submit" value="add"></form><br/>'
        
            form2 ='<form name="form2" action="/stats/flowentry/modify" method="POST" target="_self">'
            form2 +=' modify all matching flow entries: <input type="text" name="text1" size="24"> <input type="submit" name="Submit" value="modify"></form><br/>'

            form3 ='<form name="form3" action="/stats/flowentry/delete" method="POST" target="_self">'
            form3 +=' delete all matching flow entries: <input type="text" name="text1" size="24"> <input type="submit" name="Submit" value="delete"></form><br/>'
        
            #form4 ='<form name="form4" action="/stats/flowentry/clear/'+str(dp)+' method="POST" target="_self">'
            #form4 +=' delete all flow entries:<input type="submit" name="Submit" value="Delete All"> </form><br/>'

            body+=form1+form2+form3
       
        return (Response(content_type='text/html',body=body))    

        """
           

    def get_desc_stats(self, req, dpid, **_kwargs):
        dp = self.dpset.get(int(dpid))
        if dp is None:
            return Response(status=404)

        if dp.ofproto.OFP_VERSION == ofproto_v1_0.OFP_VERSION:
            desc = ofctl_v6.get_desc_stats(dp, self.waiters)
        else:
            LOG.debug('Unsupported OF protocol')
            return Response(status=501)

        body = json.dumps(desc)
        return (Response(content_type='application/json', body=body))

    def get_flow_stats(self, req, dpid, **_kwargs):
        dp = self.dpset.get(int(dpid))
        if dp is None:
            return Response(status=404)

        if dp.ofproto.OFP_VERSION == ofproto_v1_0.OFP_VERSION:
            flows = ofctl_v6.get_flow_stats(dp, self.waiters)
            #print flows
        else:
            LOG.debug('Unsupported OF protocol')
            return Response(status=501)
        body = json.dumps(flows)       
        #body = json.dumps(flows,indent=4, separators=(',', ': '),encoding='ISO-8859-1')        
        return (Response(content_type='application/json',body = body))
       

    def get_port_stats(self, req, dpid, **_kwargs):
        dp = self.dpset.get(int(dpid))
        if dp is None:
            return Response(status=404)

        if dp.ofproto.OFP_VERSION == ofproto_v1_0.OFP_VERSION:
            ports = ofctl_v6.get_port_stats(dp, self.waiters)
        else:
            LOG.debug('Unsupported OF protocol')
            return Response(status=501)

        body = json.dumps(ports)
        return (Response(content_type='application/json', body=body))

    def mod_flow_entry(self, req, cmd, **_kwargs):

        input_ = urllib.unquote(req.body)
        print input_
        """
        cmd = input_.split('&')[1].split('=')[1]
        ftemp =  input_.split('&')[0].split('=')[1]
        """

        ftemp = input_
        print '## ',ftemp
        try:
            flow = eval(ftemp)
            #print flow                      
        except SyntaxError:

            LOG.debug('invalid syntax %s', req.body)
            return Response(status=400)

        dpid = flow.get('dpid')
        dp = self.dpset.get(int(dpid))
        if dp is None:
            return 'error'
        #print flow,cmd
        if cmd == 'add':
            cmd = dp.ofproto.OFPFC_ADD
        elif cmd == 'modify':
            cmd = dp.ofproto.OFPFC_MODIFY_STRICT
        elif cmd == 'delete':
            cmd = dp.ofproto.OFPFC_DELETE_STRICT     
        else:
            return 'method error'
        if dp.ofproto.OFP_VERSION == ofproto_v1_0.OFP_VERSION:
            ofctl_v6.mod_flow_entry(dp, flow, cmd)
                          
        else:
            LOG.debug('Unsupported OF protocol')
            return 'unsupport of protocol'

        return 'success'

    def delete_flow_entry(self, req, dpid, **_kwargs):
        dp = self.dpset.get(int(dpid))
        if dp is None:
            return Response(status=404)

        if dp.ofproto.OFP_VERSION == ofproto_v1_0.OFP_VERSION:
            ofctl_v6.delete_flow_entry(dp)
        else:
            LOG.debug('Unsupported OF protocol')
            return Response(status=501)

        return Response(status=200)

           
class RestStatsApi_v6(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]
    _CONTEXTS = {
        'dpset': dpset.DPSet,
        'wsgi': WSGIApplication
    }

    def __init__(self, *args, **kwargs):
        super(RestStatsApi_v6, self).__init__(*args, **kwargs)
        self.dpset = kwargs['dpset']
        wsgi = kwargs['wsgi']
        self.waiters = {}
        self.data = {}
        self.data['dpset'] = self.dpset
        self.data['waiters'] = self.waiters
        mapper = wsgi.mapper

        wsgi.registory['StatsController'] = self.data
        
        path = '/stats'

        mapper.connect('/',
                       controller=StatsController, action='get_homepage',
                       conditions=dict(method=['GET']))
        uri = path + '/switches'
        mapper.connect('stats', uri,
                       controller=StatsController, action='get_dpids',
                       conditions=dict(method=['GET']))

        uri = path + '/desc/{dpid}'
        mapper.connect('stats', uri,
                       controller=StatsController, action='get_desc_stats',
                       conditions=dict(method=['GET']))

        uri = path + '/flow/{dpid}'
        mapper.connect('stats', uri,
                       controller=StatsController, action='get_flow_stats',
                       conditions=dict(method=['GET']))

        uri = path + '/port/{dpid}'
        mapper.connect('stats', uri,
                       controller=StatsController, action='get_port_stats',
                       conditions=dict(method=['GET']))

        uri = path + '/flowentry/{cmd}'
        mapper.connect('stats', uri,
                       controller=StatsController, action='mod_flow_entry',
                       conditions=dict(method=['POST']))

        uri = path + '/flowentry/clear/{dpid}'
        mapper.connect('stats', uri,
                       controller=StatsController, action='delete_flow_entry',
                       conditions=dict(method=['POST']))

    def stats_reply_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath

        if dp.id not in self.waiters:
            return
        if msg.xid not in self.waiters[dp.id]:
            return
        lock, msgs = self.waiters[dp.id][msg.xid]
        msgs.append(msg)

        if msg.flags & dp.ofproto.OFPSF_REPLY_MORE:
            return
        del self.waiters[dp.id][msg.xid]
        lock.set()

    @set_ev_cls(ofp_event.EventOFPDescStatsReply, MAIN_DISPATCHER)
    def desc_stats_reply_handler(self, ev):
        self.stats_reply_handler(ev)
    '''
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        self.stats_reply_handler(ev)
        print 'hello 1234'
    '''

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        self.stats_reply_handler(ev)
    
    @set_ev_cls(ofp_event.EventNXFlowStatsReply, MAIN_DISPATCHER)   
    def flow_stats_reply_handler(self, ev):
        self.stats_reply_handler(ev)        
