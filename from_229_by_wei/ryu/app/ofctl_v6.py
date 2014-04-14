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

import struct
import socket
import logging

from ryu.lib import hub

from binascii import hexlify

from ryu.ofproto import ether
from ryu.ofproto import nx_match
from ryu.ofproto import ofproto_v1_0
from ryu.lib.mac import haddr_to_bin, haddr_to_str
import convert


LOG = logging.getLogger('ryu.lib.ofctl_v1_0')

DEFAULT_TIMEOUT = 1.0   # TODO:XXX

def to_command(table,command):
        return table << 8 | command 


def to_actions(dp, acts):
    actions = []
    for a in acts:
        action_type = a.get('type')
        if action_type == 'OUTPUT':
            out_port = int(a.get('port', ofproto_v1_0.OFPP_NONE))
            actions.append(dp.ofproto_parser.OFPActionOutput(out_port))
        elif action_type == 'SET_VLAN_VID':
            vlan_vid = int(a.get('vlan_vid', 0xffff))
            actions.append(dp.ofproto_parser.OFPActionVlanVid(vlan_vid))
        elif action_type == 'SET_VLAN_PCP':
            vlan_pcp = int(a.get('vlan_pcp', 0))
            actions.append(dp.ofproto_parser.OFPActionVlanPcp(vlan_pcp))
        elif action_type == 'STRIP_VLAN':
            actions.append(dp.ofproto_parser.OFPActionStripVlan())
        elif action_type == 'SET_DL_SRC':
            dl_src = haddr_to_bin(a.get('dl_src'))
            actions.append(dp.ofproto_parser.OFPActionSetDlSrc(dl_src))
        elif action_type == 'SET_DL_DST':
            dl_dst = haddr_to_bin(a.get('dl_dst'))
            actions.append(dp.ofproto_parser.OFPActionSetDlDst(dl_dst))
        else:
            LOG.debug('Unknown action type')

    return actions
    
def to_rule(rule,_rule):
    for k,v in rule.items():
        if k == 'in_port':
            _rule.set_in_port(v)
        elif k == 'dl_vlan':
            _rule.set_dl_vlan(v)
        elif k == 'set_dl_vlan_pcp':
            _rule.set_dl_vlan_pcp(v)
        elif k == 'dl_src':
            _rule.set_dl_src(convert.haddr_to_bin(v))
        elif k == 'dl_dst':
            _rule.set_dl_dst(convert.haddr_to_bin(v))
        elif k == 'dl_type':
            _rule.set_dl_type(v)

        elif k == 'nw_proto':
            _rule.set_nw_proto(v)
        elif k == 'tp_dst':
            _rule.set_tp_dst(v)
        elif k == 'tp_src':
            _rule.set_tp_src(v)

        elif k == 'nw_src':
            _rule.set_nw_src(convert.ipv4_to_int(v))
        elif k == 'nw_src_masked':
            if _rule.flow.nw_src != 0:
                _rule.set_nw_src_masked(_rule.flow.nw_src,convert.ipv4_prefix_to_bin(v))
        elif k == 'nw_dst':
            _rule.set_nw_dst(convert.ipv4_to_int(v))
        elif k == 'nw_dst_masked':
            if _rule.flow.nw_dst != 0:
                _rule.set_nw_dst_masked(_rule.flow.nw_dst,convert.ipv4_prefix_to_bin(v))
        elif k == 'ipv6_label':
            _rule.set_ipv6_label(v)
        elif k == 'ipv6_src':
            _rule.set_ipv6_src(convert.ipv6_to_arg_list(v))
        elif k == 'ipv6_src_masked':
            if _rule.flow.ipv6_src != []:
                _rule.set_ipv6_src_masked(_rule.flow.ipv6_src,convert.ipv6_prefix_to_arg_list(v))       
        elif k == 'ipv6_dst':
            _rule.set_ipv6_dst(convert.ipv6_to_arg_list(v))            
        elif k == 'ipv6_dst_masked':
            if _rule.flow.ipv6_dst != []:
                _rule.set_ipv6_dst_masked(_rule.flow.ipv6_dst,convert.ipv6_prefix_to_arg_list(v))
        elif k == 'tun_id':
            _rule.set_tun_id(v)
            print 'kkk',k
        else:
            pass
    return _rule    


def str_to_ipv6_add(_str):
    
     return convert.ipv6_to_bin(_str)
   

def ipv6_add_to_str(binary):

    return convert.ipv6_arg_list_to_str(binary)




def actions_to_str(acts):
    actions = []
    for a in acts:
        action_type = a.cls_action_type
        if action_type == ofproto_v1_0.OFPAT_OUTPUT:
            buf = 'OUTPUT:' + str(a.port)
        elif action_type == ofproto_v1_0.OFPAT_SET_VLAN_VID:
            buf = 'SET_VLAN_VID:' + str(a.vlan_vid)
        elif action_type == ofproto_v1_0.OFPAT_SET_VLAN_PCP:
            buf = 'SET_VLAN_PCP:' + str(a.vlan_pcp)
        elif action_type == ofproto_v1_0.OFPAT_STRIP_VLAN:
            buf = 'STRIP_VLAN'
        elif action_type == ofproto_v1_0.OFPAT_SET_DL_SRC:
            buf = 'SET_DL_SRC:' + haddr_to_str(a.dl_addr)
        elif action_type == ofproto_v1_0.OFPAT_SET_DL_DST:
            buf = 'SET_DL_DST:' + haddr_to_str(a.dl_addr)
        elif action_type==65535:
            if a.subtype==2:
                buf = 'set_tunnel:'+str(a.tun_id)
            else:
                buf='resubmit:(,'+str(a.table)+')'
        else:
            buf='UNKNOWN'
        actions.append(buf)

    return actions


def to_match(dp, attrs):
    ofp = dp.ofproto

    wildcards = ofp.OFPFW_ALL
    in_port = 0
    dl_src = 0
    dl_dst = 0
    dl_vlan = 0
    dl_vlan_pcp = 0
    dl_type = 0
    nw_tos = 0
    nw_proto = 0
    nw_src = 0
    nw_dst = 0
    tp_src = 0
    tp_dst = 0

    for key, value in attrs.items():
        if key == 'in_port':
            in_port = int(value)
            wildcards &= ~ofp.OFPFW_IN_PORT
        elif key == 'dl_src':
            dl_src = haddr_to_bin(value)
            wildcards &= ~ofp.OFPFW_DL_DST
        elif key == 'dl_dst':
            dl_dst = haddr_to_bin(value)
            wildcards &= ~ofp.OFPFW_DL_DST
        elif key == 'dl_vlan':
            dl_vlan = int(value)
            wildcards &= ~ofp.OFPFW_DL_VLAN
        elif key == 'dl_vlan_pcp':
            dl_vlan_pcp = int(value)
            wildcards &= ~ofp.OFPFW_DL_VLAN_PCP
        elif key == 'dl_type':
            dl_type = int(value)
            wildcards &= ~ofp.OFPFW_DL_TYPE
        elif key == 'nw_tos':
            nw_tos = int(value)
            wildcards &= ~ofp.OFPFW_NW_TOS
        elif key == 'nw_proto':
            nw_proto = int(value)
            wildcards &= ~ofp.OFPFW_NW_PROTO
        elif key == 'nw_src':
            ip = value.split('/')
            nw_src = struct.unpack('!I', socket.inet_aton(ip[0]))[0]
            mask = 32
            if len(ip) == 2:
                mask = int(ip[1])
                assert 0 < mask <= 32
            v = (32 - mask) << ofp.OFPFW_NW_SRC_SHIFT | \
                ~ofp.OFPFW_NW_SRC_MASK
            wildcards &= v
        elif key == 'nw_dst':
            ip = value.split('/')
            nw_dst = struct.unpack('!I', socket.inet_aton(ip[0]))[0]
            mask = 32
            if len(ip) == 2:
                mask = int(ip[1])
                assert 0 < mask <= 32
            v = (32 - mask) << ofp.OFPFW_NW_DST_SHIFT | \
                ~ofp.OFPFW_NW_DST_MASK
            wildcards &= v
        elif key == 'tp_src':
            tp_src = int(value)
            wildcards &= ~ofp.OFPFW_TP_SRC
        elif key == 'tp_dst':
            tp_dst = int(value)
            wildcards &= ~ofp.OFPFW_TP_DST
        else:
            LOG.debug("unknown match name %s, %s, %d", key, value, len(key))

    match = dp.ofproto_parser.OFPMatch(
        wildcards, in_port, dl_src, dl_dst, dl_vlan, dl_vlan_pcp,
        dl_type, nw_tos, nw_proto, nw_src, nw_dst, tp_src, tp_dst)

    return match


def match_to_str(m):
    return {'dl_dst': haddr_to_str(m.dl_dst),
            'dl_src': haddr_to_str(m.dl_src),
            'dl_type': m.dl_type,
            'dl_vlan': m.dl_vlan,
            'dl_vlan_pcp': m.dl_vlan_pcp,
            'in_port': m.in_port,
            'nw_dst': socket.inet_ntoa(struct.pack('!I', m.nw_dst)),
            'nw_proto': m.nw_proto,
            'nw_src': socket.inet_ntoa(struct.pack('!I', m.nw_src)),
            'tp_src': m.tp_src,
            'tp_dst': m.tp_dst}


def send_stats_request(dp, stats, waiters, msgs):
    dp.set_xid(stats)
    waiters_per_dp = waiters.setdefault(dp.id, {})
    lock = hub.Event()
    waiters_per_dp[stats.xid] = (lock, msgs)
    dp.send_msg(stats)

    try:
        lock.wait(timeout=DEFAULT_TIMEOUT)
    except hub.Timeout:
        del waiters_per_dp[stats.xid]


def get_desc_stats(dp, waiters):
    stats = dp.ofproto_parser.OFPDescStatsRequest(dp, 0)
    msgs = []
    send_stats_request(dp, stats, waiters, msgs)
    s = {}
    for msg in msgs:
        stats = msg.body
        s = {'mfr_desc': stats.mfr_desc,
             'hw_desc': stats.hw_desc,
             'sw_desc': stats.sw_desc,
             'serial_num': stats.serial_num,
             'dp_desc': stats.dp_desc}
    desc = {str(dp.id): s}
    return desc


def get_flow_stats(dp, waiters):
    
    rule = nx_match.ClsRule()
    stats = dp.ofproto_parser.NXFlowStatsRequest(datapath = dp,
            flags = 0, out_port = dp.ofproto.OFPP_NONE, table_id = 0xff)
    msgs = []

    send_stats_request(dp, stats, waiters, msgs)
    flows =[]
    for msg in msgs:        
        for body in msg.body:
            actions = actions_to_str(body.actions)   
            s = {'cookie':hex(body.cookie),
                 'duration': str(body.duration_sec) +'.'+ str(body.duration_nsec),
                 'table_id':body.table_id,
                 'n_packets':body.packet_count,
                 'n_bytes':body.byte_count,
                 'idle_age':body.idle_age,
                 'priority':body.priority,
                 'nx_match':[],
                 'actions':actions
            }
            _dict = {} 
            for field in body.fields:

                if field.nxm_header == ofproto_v1_0.NXM_OF_IN_PORT:
                    _dict['in_port'] = hex(field.value)
                elif field.nxm_header ==  ofproto_v1_0.NXM_OF_ETH_SRC:
                    _dict['dl_src'] = haddr_to_str(field.value)
                elif field.nxm_header ==  ofproto_v1_0.NXM_OF_ETH_DST:
                    _dict['dl_dst'] = haddr_to_str(field.value)

                elif field.nxm_header ==  ofproto_v1_0.NXM_OF_ETH_TYPE:
                    _dict['dl_type'] = hex(field.value)
                    

                elif field.nxm_header == ofproto_v1_0.NXM_OF_IP_SRC:
                    _dict['nw_src'] = convert.ipv4_to_str(field.value)
                    
                elif field.nxm_header == ofproto_v1_0.NXM_OF_IP_SRC_W:
                    _dict['nw_src'] = convert.ipv4_to_str(field.value)
                    _dict['nw_src_masked'] = convert.bin_to_ipv4_prefix(field.mask)
                    
                elif field.nxm_header == ofproto_v1_0.NXM_OF_IP_DST:
                    _dict['nw_dst'] = convert.ipv4_to_str(field.value)
                    
                elif field.nxm_header == ofproto_v1_0.NXM_OF_IP_DST_W:
                    _dict['nw_dst'] = convert.ipv4_to_str(field.value)
                    _dict['nw_dst_masked'] = convert.ipv4_to_str(field.mask)

                elif field.nxm_header == ofproto_v1_0.NXM_NX_TUN_ID :
                    _dict['tun_id'] = hex(field.value)

                elif field.nxm_header == ofproto_v1_0.NXM_OF_TCP_SRC:
                    _dict['tp_src'] = field.value

                elif field.nxm_header == ofproto_v1_0.NXM_OF_TCP_DST:
                    _dict['tp_dst'] = field.value

                elif field.nxm_header == ofproto_v1_0.NXM_OF_IP_PROTO:
                    _dict['nw_proto'] = field.value 


                elif field.nxm_header == ofproto_v1_0.NXM_NX_IPV6_SRC:
                    #print '****',field.value
                    _dict['ipv6_src'] = ipv6_add_to_str(field.value)

                elif field.nxm_header == ofproto_v1_0.NXM_NX_IPV6_SRC_W:                    
                    _dict['ipv6_src'] = ipv6_add_to_str(field.value)
                    _dict['ipv6_src_masked'] = convert.arg_list_to_ipv6_prefix(field.mask)
                    
                elif field.nxm_header == ofproto_v1_0.NXM_NX_IPV6_DST:
                    _dict['ipv6_dst'] = ipv6_add_to_str(field.value) 

                elif field.nxm_header == ofproto_v1_0.NXM_NX_IPV6_DST_W:
                    _dict['ipv6_dst'] = ipv6_add_to_str(field.value)
                    _dict['ipv6_dst_masked'] = convert.arg_list_to_ipv6_prefix(field.mask)         
                else:
		    pass
		"""
                    try:
                        _dict['value'] =  hex(field.value)
                    except:
                        _dict['value'] = ''.join(c for c in field.value)
                """
            s['nx_match'].append(_dict)
            flows.append(s)
    flows = {str(dp.id): flows}                   
    return flows

def get_port_stats(dp, waiters):
    stats = dp.ofproto_parser.OFPPortStatsRequest(
        dp, 0, dp.ofproto.OFPP_NONE)
    msgs = []
    send_stats_request(dp, stats, waiters, msgs)

    ports = []
    for msg in msgs:
        for stats in msg.body:
            s = {'port_no': stats.port_no,
                 'rx_packets': stats.rx_packets,
                 'tx_packets': stats.tx_packets,
                 'rx_bytes': stats.rx_bytes,
                 'tx_bytes': stats.tx_bytes,
                 'rx_dropped': stats.rx_dropped,
                 'tx_dropped': stats.tx_dropped,
                 'rx_errors': stats.rx_errors,
                 'tx_errors': stats.tx_errors,
                 'rx_frame_err': stats.rx_frame_err,
                 'rx_over_err': stats.rx_over_err,
                 'rx_crc_err': stats.rx_crc_err,
                 'collisions': stats.collisions}
            ports.append(s)
    ports = {str(dp.id): ports}
    return ports


def mod_flow_entry(dp, flow, cmd):
   
    cookie = int(flow.get('cookie', 0))   
    idle_timeout = int(flow.get('idle_timeout', 0))   
    priority = int(flow.get('priority',dp.ofproto.OFP_DEFAULT_PRIORITY))
    _rule = nx_match.ClsRule()  

    #{'dpid':1,'rule':{'dl_type':0x86dd,'ipv6_src':'10:0:0:0:0:0:0:1'}}
    rule = to_rule(flow.get('rule',{}),_rule)    
    #if have several tables,table_id is necessary--lee
    # modify can only change the actions,eg OUTPUT:2   
    command = to_command(0,cmd)
    hard_timeout = int(flow.get('hard_timeout', 0))
    buffer_id = int(flow.get('buffer_id','ffffffff'),16)
    out_port = int(flow.get('out_port',dp.ofproto.OFPP_NONE))
    flags = int(flow.get('flags', 0))
    actions = to_actions(dp, flow.get('actions', {})) 
    
    flow_mod = dp.ofproto_parser.NXTFlowMod(datapath=dp,
        cookie=cookie, command=command, idle_timeout=idle_timeout, hard_timeout=hard_timeout,
        priority=priority, buffer_id=buffer_id,
        out_port=out_port,
        flags=flags, rule= rule, actions=actions)
   
    dp.send_msg(flow_mod)


def delete_flow_entry(dp):
    match = dp.ofproto_parser.OFPMatch(
        dp.ofproto.OFPFW_ALL, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    flow_mod = dp.ofproto_parser.OFPFlowMod(
        datapath=dp, match=match, cookie=0,
        command=dp.ofproto.OFPFC_DELETE)

    dp.send_msg(flow_mod)