#!/usr/bin/env python3

'''
Basic IPv4 router (static routing) in Python.
'''
import os
import sys
import time
import switchyard
from datetime import datetime
from switchyard.lib.userlib import *
from switchyard.lib.address import *
#from switchyard.lib.packet.Arp import *
class Queue(object):
    def __init__(self, net: switchyard.llnetbase.LLNetBase):
        self.net=net
        self.cache = {}#list in table : dstipaddr[datetime,interface,try number,[packets]]
    def push(self,dstipaddr,intf,packet):
        if dstipaddr in self.cache:
            self.cache[dstipaddr][3].append(packet)
        else:
            arp_request=create_ip_arp_request(intf.ethaddr,intf.ipaddr,dstipaddr)
            self.net.send_packet(intf,arp_request)
            self.cache[dstipaddr]=[datetime.now(),intf,1,[packet]]
    def send_packet(self,arp_table,forwarding_table,router):
        for dstipaddr in list(self.cache.keys()):
            if dstipaddr in arp_table:
                for packet in self.cache[dstipaddr][3]:
                    packet[Ethernet].dst=arp_table[dstipaddr][0]
                    self.net.send_packet(self.cache[dstipaddr][1],packet)
                del self.cache[dstipaddr]
            else:
                elapsed_time=datetime.now().timestamp()-self.cache[dstipaddr][0].timestamp()
                if elapsed_time>=1:
                    if self.cache[dstipaddr][2]>=5:
                        for packet in self.cache[dstipaddr][3]:
                            i = packet.get_header_index(Ethernet)
                # remove Ethernet header --- the errored packet contents sent with
                # the ICMP error message should not have an Ethernet header
                            del packet[i]
                            icmp = ICMP()
                            icmp.icmptype = ICMPType.DestinationUnreachable
                            icmp.icmpcode = ICMPTypeCodeMap[icmp.icmptype].HostUnreachable
                            icmp.icmpdata.data = packet.to_bytes()[:28]
                            print(icmp)
            # ICMP TimeExceeded:TTLExpired 28 bytes of raw payload 
            # (b'E\x00\x00\x1c\x00\x00\x00\x00\x00\x01') OrigDgramLen: 0
                            ip = IPv4()
                            ip.protocol = IPProtocol.ICMP
                            longest_prefixlen = 0
                            match = None
                            for entry in forwarding_table:
                                entry_netaddr= IPv4Network(entry[0]+'/'+entry[1],strict = False)
                                if packet[IPv4].src in entry_netaddr:
                                    if entry_netaddr.prefixlen > longest_prefixlen:
                                        longest_prefixlen = entry_netaddr.prefixlen
                                        match = entry
                            ip.src = self.net.interface_by_name(match[3]).ipaddr
                            ip.dst = packet[IPv4].src
                            ip.ttl = 64
                            ether = Ethernet()
                            ether.ethertype = EtherType.IPv4
                            new_packet = ether + ip + icmp
                            router.forward_packet(match,new_packet,packet[IPv4].src)
                        del self.cache[dstipaddr]
                    else:
                        self.cache[dstipaddr][2]+=1
                        self.cache[dstipaddr][0]=datetime.now()
                        arp_request=create_ip_arp_request(self.cache[dstipaddr][1].ethaddr,self.cache[dstipaddr][1].ipaddr,dstipaddr)
                        self.net.send_packet(self.cache[dstipaddr][1],arp_request)

class Router(object):
    def __init__(self, net: switchyard.llnetbase.LLNetBase):
        self.net = net
        self.arp_table={}
        self.Queue = Queue(net)
        self.forwarding_table = []# Forwarding table: [[network addresss, subnet mask, next hop IPaddr, assigned interface]]
        for intf in self.net.interfaces():
            self.forwarding_table.append([str(intf.ipaddr),str(intf.netmask),None,intf.name])#router interface
        fo = open("forwarding_table.txt","r+")
        lines = fo.readlines()
        for line in lines :
            self.forwarding_table.append(line.split())#list type
        fo.close()
        print(self.forwarding_table)

        # other initialization stuff here
    def forward_packet(self,match,packet,dstip):
        match_intf = None
        interfaces=self.net.interfaces()
        for intf in interfaces:
            if match[3] == intf.name:
                match_intf=intf
                break
        packet[Ethernet].src=match_intf.ethaddr
        if match[2] is None:
            if dstip in self.arp_table:
                packet[Ethernet].dst=self.arp_table[dstip][0]
                self.net.send_packet(match_intf,packet)
            else:
                self.Queue.push(dstip, match_intf, packet)            
        else:
            if IPv4Address(match[2]) in self.arp_table:
                packet[Ethernet].dst=self.arp_table[IPv4Address(match[2])][0]
                self.net.send_packet(match_intf,packet)
            else:
                self.Queue.push(IPv4Address(match[2]), match_intf, packet)  
    def handle_packet(self, recv: switchyard.llnetbase.ReceivedPacket):
        timestamp, ifaceName, packet = recv
        arp=packet.get_header(Arp)
        interfaces = self.net.interfaces()
        if not arp is None:
            self.arp_table[arp.senderprotoaddr] = [arp.senderhwaddr,datetime.now()]
            print(self.arp_table)
            if arp.operation == 1:
                targetprotoaddr = arp.targetprotoaddr
                target = None                  
                for intf in interfaces:
                    if intf.ipaddr == targetprotoaddr:
                        target = intf
                        break

                if not target is None:
                    arp_reply = create_ip_arp_reply(target.ethaddr,arp.senderhwaddr,target.ipaddr,arp.senderprotoaddr)
                    for intf in interfaces:
                        if intf.name == ifaceName:
                            self.net.send_packet(intf,arp_reply)
                            break
        # TODO: your logic here



        ipV4=packet.get_header(IPv4)
        if( ipV4 is not None ):
            for intf in interfaces:
                if ipV4.dst == intf.ipaddr:
                    icmp=packet.get_header(ICMP)
                    if icmp is not None:
                        if icmp.icmptype == ICMPType.EchoRequest:
                            echo_reply=ICMP()
                            echo_reply.icmptype=ICMPType.EchoReply
                            echo_reply.icmpdata.sequence=icmp.icmpdata.sequence
                            echo_reply.icmpdata.identifier=icmp.icmpdata.identifier
                            echo_reply.icmpdata.data=icmp.icmpdata.data
                            ipV4.dst=ipV4.src
                            ipV4.src=intf.ipaddr
                            packet[packet.get_header_index(ICMP)]=echo_reply
                            break
            longest_prefixlen = 0
            match = None
            for entry in self.forwarding_table:
                entry_netaddr= IPv4Network(entry[0]+'/'+entry[1],strict = False)
                if ipV4.dst in entry_netaddr:
                    if entry_netaddr.prefixlen > longest_prefixlen:
                        longest_prefixlen = entry_netaddr.prefixlen
                        match = entry
        
            if not match is None:
                flag = True 
                for intf in interfaces:
                    if ipV4.dst == intf.ipaddr :#if the destination ipaddress is one ipaddress of thr router
                        flag = False
                        break
                if flag :
                    packet[IPv4].ttl-=1
                    if packet[IPv4].ttl <= 0:#ttl consumed
                        i = packet.get_header_index(Ethernet)
                        # remove Ethernet header --- the errored packet contents sent with
                        # the ICMP error message should not have an Ethernet header
                        del packet[i]
                        icmp = ICMP()
                        icmp.icmptype = ICMPType.TimeExceeded
                        icmp.icmpcode = ICMPTypeCodeMap[icmp.icmptype].TTLExpired
                        icmp.icmpdata.data = packet.to_bytes()[:28]
                        print(icmp)
                        # ICMP TimeExceeded:TTLExpired 28 bytes of raw payload 
                        # (b'E\x00\x00\x1c\x00\x00\x00\x00\x00\x01') OrigDgramLen: 0
                        ip = IPv4()
                        ip.protocol = IPProtocol.ICMP
                        longest_prefixlen = 0
                        match = None
                        for entry in self.forwarding_table:
                            entry_netaddr= IPv4Network(entry[0]+'/'+entry[1],strict = False)
                            if packet[IPv4].src in entry_netaddr:
                                if entry_netaddr.prefixlen > longest_prefixlen:
                                    longest_prefixlen = entry_netaddr.prefixlen
                                    match = entry
                        ip.src = self.net.interface_by_name(match[3]).ipaddr
                        ip.dst = packet[IPv4].src
                        ip.ttl = 64
                        ether = Ethernet()
                        ether.ethertype = EtherType.IPv4
                        new_packet = ether + ip + icmp
                        self.forward_packet(match,new_packet,packet[IPv4].src)
                    else:
                        self.forward_packet(match,packet,ipV4.dst)
                else:#not echo request
                    i = packet.get_header_index(Ethernet)
                    # remove Ethernet header --- the errored packet contents sent with
                    # the ICMP error message should not have an Ethernet header
                    del packet[i]
                    icmp = ICMP()
                    icmp.icmptype = ICMPType.DestinationUnreachable
                    icmp.icmpcode = ICMPTypeCodeMap[icmp.icmptype].PortUnreachable
                    icmp.icmpdata.data = packet.to_bytes()[:28]
                    print(icmp)
                    # ICMP TimeExceeded:TTLExpired 28 bytes of raw payload 
                    # (b'E\x00\x00\x1c\x00\x00\x00\x00\x00\x01') OrigDgramLen: 0
                    ip = IPv4()
                    ip.protocol = IPProtocol.ICMP
                    longest_prefixlen = 0
                    match = None
                    for entry in self.forwarding_table:
                        entry_netaddr= IPv4Network(entry[0]+'/'+entry[1],strict = False)
                        if packet[IPv4].src in entry_netaddr:
                            if entry_netaddr.prefixlen > longest_prefixlen:
                                longest_prefixlen = entry_netaddr.prefixlen
                                match = entry
                    ip.src = self.net.interface_by_name(match[3]).ipaddr
                    ip.dst = packet[IPv4].src
                    ip.ttl = 64
                    ether = Ethernet()
                    ether.ethertype = EtherType.IPv4
                    new_packet = ether + ip + icmp
                    self.forward_packet(match,new_packet,packet[IPv4].src)
            else:#match is None
                i = packet.get_header_index(Ethernet)
                # remove Ethernet header --- the errored packet contents sent with
                # the ICMP error message should not have an Ethernet header
                del packet[i]
                icmp = ICMP()
                icmp.icmptype = ICMPType.DestinationUnreachable
                icmp.icmpcode = ICMPTypeCodeMap[icmp.icmptype].NetworkUnreachable
                icmp.icmpdata.data = packet.to_bytes()[:28]
                print(icmp)
                # ICMP TimeExceeded:TTLExpired 28 bytes of raw payload 
                #   (b'E\x00\x00\x1c\x00\x00\x00\x00\x00\x01') OrigDgramLen: 0
                ip = IPv4()
                ip.protocol = IPProtocol.ICMP
                longest_prefixlen = 0
                match = None
                for entry in self.forwarding_table:
                    entry_netaddr= IPv4Network(entry[0]+'/'+entry[1],strict = False)
                    if packet[IPv4].src in entry_netaddr:
                        if entry_netaddr.prefixlen > longest_prefixlen:
                            longest_prefixlen = entry_netaddr.prefixlen
                            match = entry
                ip.src = self.net.interface_by_name(match[3]).ipaddr
                ip.dst = packet[IPv4].src
                ip.ttl = 64
                ether = Ethernet()
                ether.ethertype = EtherType.IPv4
                new_packet = ether + ip + icmp
                self.forward_packet(match,new_packet,packet[IPv4].src)
# protocol defaults to ICMP
# setting it explicitly here anyway

# would also need to set ip.src, ip.dst, and ip.ttl to 
# something non-zero

    
        else:
            pass
                    
        

    def start(self):
        '''A running daemon of the router.
        Receive packets until the end of time.
        '''
        while True:
            self.Queue.send_packet(self.arp_table,self.forwarding_table,self)
            now=datetime.now()
            for key in list(self.arp_table.keys()):
                elapsed_time=now.timestamp() - self.arp_table[key][1].timestamp()
                if elapsed_time>=1000000:
                    del self.arp_table[key]
                    log_info (f"table entry with IP Address {key} has been removed from  arp_table ")
 
            try:
                recv = self.net.recv_packet(timeout=1.0)
            except NoPackets:
                continue
            except Shutdown:
                break

            self.handle_packet(recv)

        self.stop()

    def stop(self):
        self.net.shutdown()


def main(net):
    '''
    Main entry point for router.  Just create Router
    object and get it going.
    '''
    router = Router(net)
    router.start()
