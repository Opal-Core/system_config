#SerialConfig.py

import configparser
import io
import ipaddress
import os
from socket import AF_INET
from dbus import Interface
import netifaces
import yaml
import re
import serial
import socket
import struct
import subprocess
import sys
import time

def io_echo_read_until(io, expected):
    cmd = ''
    while True:
        try:
            b = io.read(1)
            if b == expected:
                return cmd
            else:
                if b == b'\b':
                    if len(cmd):
                        cmd = cmd[:-1]
                        io.write(b'\b \b')
                elif b != b'\x1b':
                    cmd = cmd + b.decode('utf-8')
                    io.write(b)
        except UnicodeDecodeError:
            pass

def print_help_main(io, args):
    io.write('\r\n'.encode('utf-8'))
    io.write('Command                   Description\r\n'.encode('utf-8'))
    io.write('------------------------------------------------------------------------------\r\n'.encode('utf-8'))
    io.write('help or h or ?            Prints available commands and descriptions\r\n'.encode('utf-8'))
    io.write('reboot                    Reboot the system. Requires confirmation\r\n'.encode('utf-8'))
    io.write('shutdown                  Shutdown the system. Requires confirmation\r\n'.encode('utf-8'))
    io.write('start all                 Start or restart all Opal servers\r\n'.encode('utf-8'))
    io.write('start vm[0-7]             Start Opal server specified by number in range\r\n'.encode('utf-8'))
    io.write('stop all                  Stop all Opal servers\r\n'.encode('utf-8'))
    io.write('stop vm[0-7]              Stop Opal server specified by number in range\r\n'.encode('utf-8'))
    io.write('print vm[0-7]             Print configuration for Opal server specified by\r\n'.encode('utf-8'))
    io.write('                          number in range\r\n'.encode('utf-8'))
    io.write('config vm[0-7]            Modify configuration for Opal server specified by\r\n'.encode('utf-8'))
    io.write('                          number in range\r\n'.encode('utf-8'))
    io.write('print net                 Print network configuration and details\r\n'.encode('utf-8'))
    io.write('config net                Modify configuration for ethernet interfaces\r\n'.encode('utf-8'))
    io.write('factory reset             Reset system to factory defaults\r\n'.encode('utf-8'))
    io.write('------------------------------------------------------------------------------'.encode('utf-8'))

def do_reboot(io, args):
    io.write('\r\n> Please confirm reboot (yes or y): '.encode('utf-8'))
    cmd = io_echo_read_until(io, b'\r').strip()
    if cmd in {'y', 'yes'}:
        io.write('\r\nRebooting now\r\n'.encode('utf-8'))
        os.system('reboot now')
    else:
        io.write('\r\nReboot canceled'.encode('utf-8'))

def do_shutdown(io, args):
    io.write('\r\n> Please confirm shutdown (yes or y): '.encode('utf-8'))
    cmd = io_echo_read_until(io, b'\r').strip()
    if cmd in {'y', 'yes'}:
        io.write('\r\nShutting down now\r\n'.encode('utf-8'))
        os.system('shutdown now')
    else:
        io.write('\r\nShutdown canceled'.encode('utf-8'))

def do_start_all(io, args):
    for n in range(8):
        os.system('update-service -r /var/lib/supervise/vm{}'.format(n))
    for n in range(8):
        os.system('update-service -a /var/lib/supervise/vm{}'.format(n))
    io.write('\r\nRestarted all servers'.encode('utf-8'))

def do_start_one(io, args):
    os.system('update-service -r /var/lib/supervise/{}'.format(args[0]))
    os.system('update-service -a /var/lib/supervise/{}'.format(args[0]))
    io.write('\r\nRestarted server {}'.format(args[0]).encode('utf-8'))

def do_stop_all(io, args):
    for n in range(8):
        os.system('update-service -r /var/lib/supervise/vm{}'.format(n))
    io.write('\r\nStopped all servers'.encode('utf-8'))

def do_stop_one(io, args):
    os.system('update-service -r /var/lib/supervise/{}'.format(args[0]))
    io.write('\r\nStopped server {}'.format(args[0]).encode('utf-8'))

def do_print_one(io, args):
    try:
        with open('/home/opal/proxy/config/{}'.format(args[0])) as f:
            io.write('\r\n'.encode('utf-8'))
            for line in f:
                io.write('{}\r'.format(line).encode('utf-8'))
    except OSError:
        io.write('\r\nCould not open configuration for for server {}'.format(args[0]).encode('utf-8'))

def do_print_sections(io, config, args):
    io.write('\r\nSections:'.encode('utf-8'))
    io.write('\r\n----------------------------------------'.encode('utf-8'))
    for idx, s in enumerate(config.sections()):
        io.write('\r\n{}. {}'.format(idx, s).encode('utf-8'))
    io.write('\r\n----------------------------------------'.encode('utf-8'))

def do_print_options(io, config, section):
    if section == '':
        io.write('A configuration section must be selected'.encode('utf-8'))
    else:
        io.write('\r\nOptions:'.encode('utf-8'))
        io.write('\r\n----------------------------------------'.encode('utf-8'))
        for idx, option in enumerate(config[section]):
            io.write('\r\n{}. {}={}'.format(idx, option, config[section][option]).encode('utf-8'))
        io.write('\r\n----------------------------------------'.encode('utf-8'))

def do_config_one(io, args):
    hasChanged = False
    filename = '/home/opal/proxy/config/{}'.format(args[0])
    config = configparser.ConfigParser()
    config.read(filename)
    while True:
        io.write('\r\n'.encode('utf-8'))
        do_print_sections(io, config, None) 
        io.write('\r\n> Enter section number (b to go back): '.encode('utf-8'))
        cmd = io_echo_read_until(io, b'\r').strip()
        if (cmd == 'b'):
            if hasChanged:
                io.write('\r\n> Save changes (yes or y): '.encode('utf-8'))
                cmd = io_echo_read_until(io, b'\r').strip()
                if cmd in {'yes', 'y'}:
                    with open(filename, 'w') as f:
                        config.write(f)
                    io.write('\r\nServer {} will need to be restarted for changes to take effect\r\n'.format(args[0]).encode('utf-8'))
                else:
                    io.write('\r\nConfiguration changes not saved\r\n'.encode('utf-8'))
            else:
                io.write('\r\nConfiguration not updated\r\n'.encode('utf-8'))
            break
        try:
            section = config.sections()[int(cmd)]
            while True:
                io.write('\r\n'.encode('utf-8'))
                do_print_options(io, config, section)
                io.write('\r\n> Enter option number (b to go back): '.encode('utf-8'))
                cmd = io_echo_read_until(io, b'\r').strip()
                if cmd == 'b':
                    break
                try:
                    optionIdx = int(cmd)
                    option = list(enumerate(config[section]))[optionIdx][1]
                    io.write('\r\n> Enter new value for {}: '.format(option).encode('utf-8'))
                    cmd = io_echo_read_until(io, b'\r').strip()
                    if (cmd != ''):
                        config[section][option] = cmd
                        hasChanged = True
                except (ValueError, IndexError):
                    io.write('\r\nInvalid option selection'.encode('utf-8'))
        except (ValueError, IndexError):
            io.write('\r\nInvalid section selection'.encode('utf-8'))

def get_interface_ip4_addrs(if_addrs):
    ip4_addrs = []
    if netifaces.AF_INET in if_addrs:
        ip4_addrs = if_addrs[netifaces.AF_INET]
    return ip4_addrs

def cidr_to_netmask(cidr):
    network, net_bits = cidr.split('/')
    host_bits = 32 - int(net_bits)
    netmask = socket.inet_ntoa(struct.pack('!I', (1 << 32) - (1 << host_bits)))
    return network, netmask

def netmask_to_cidr(netmask):
    return sum([bin(int(x)).count('1') for x in netmask.split('.')])

def do_print_netplan(io, netplan, interface):
    if netplan != None and 'ethernets' in netplan['network'] and interface in netplan['network']['ethernets']:
        if 'dhcp4' in netplan['network']['ethernets'][interface] and netplan['network']['ethernets'][interface]['dhcp4'] == True:
            io.write('\r\n  automatic (DHCP)'.encode('utf-8'))
        else:
            if 'addresses' in netplan['network']['ethernets'][interface]:
                if len(netplan['network']['ethernets'][interface]['addresses']):
                    addr, mask = cidr_to_netmask(netplan['network']['ethernets'][interface]['addresses'][0])
                    io.write('\r\n  address: {}'.format(addr).encode('utf-8'))
                    io.write('\r\n  netmask: {}'.format(mask).encode('utf-8'))
            if 'routes' in netplan['network']['ethernets'][interface]:
                for r in netplan['network']['ethernets'][interface]['routes']:
                    io.write('\r\n  gateway: {}'.format(r['via']).encode('utf-8'))
            if 'nameservers' in netplan['network']['ethernets'][interface]:
                if 'addresses' in netplan['network']['ethernets'][interface]['nameservers']:
                    for a in netplan['network']['ethernets'][interface]['nameservers']['addresses']:
                        io.write('\r\n  nameserver: {}'.format(a).encode('utf-8'))
    else:
        io.write('\r\n  Static'.encode('utf-8'))

def do_print_net(io, args):
    netplan = None
    try:
        with open('/etc/netplan/01-network-manager-all.yaml') as f:
            netplan = yaml.load(f, Loader=yaml.FullLoader)
    except OSError:
        io.write('\r\nCould not open network configuration file {}'.format(args[0]).encode('utf-8'))

    gateways = netifaces.gateways()
    for interface in netifaces.interfaces():
        if interface.startswith('e'):
            io.write('\r\n\r\n----------------------------------------'.encode('utf-8'))
            io.write('\r\ninterface: {}'.format(interface).encode('utf-8'))
            ip4_addrs = get_interface_ip4_addrs(netifaces.ifaddresses(interface))
            if (len(ip4_addrs) == 0):
                io.write('\r\navailable: No'.encode('utf-8'))
                io.write('\r\nconfiguration:'.encode('utf-8'))
                do_print_netplan(io, netplan, interface)
            else:
                io.write('\r\navailable: Yes'.encode('utf-8'))
                io.write('\r\nconfiguration:'.encode('utf-8'))
                do_print_netplan(io, netplan, interface)

                io.write('\r\ndetails:'.encode('utf-8'))
                for addr in ip4_addrs:
                    io.write('\r\n  address: {}'.format(addr['addr']).encode('utf-8'))
                    io.write('\r\n  netmask: {}'.format(addr['netmask']).encode('utf-8'))
                    if (netifaces.AF_INET in gateways):
                        for gw in gateways[netifaces.AF_INET]:
                            if interface == gw[1]:
                                io.write('\r\n  gateway: {}'.format(gw[0]).encode('utf-8'))
                    io.write('\r\n  broadcast: {}'.format(addr['broadcast']).encode('utf-8'))
    io.write('\r\n'.encode('utf-8'))

def do_config_net(io, args):
    netplan = None
    try:
        with open('/etc/netplan/01-network-manager-all.yaml') as f:
            netplan = yaml.load(f, Loader=yaml.FullLoader)
    except OSError:
        io.write('\r\nCould not open network configuration file {}'.format('/etc/netplan/01-network-manager-all.yaml').encode('utf-8'))

    ethernet_interfaces = []
    for interface in netifaces.interfaces():
        if interface.startswith('e'):
            ethernet_interfaces.append(interface)

    hasChanged = False
    try:
        while True:
            io.write('\r\n\r\nEthernet interfaces:'.encode('utf-8'))
            io.write('\r\n----------------------------------------'.encode('utf-8'))
            for idx, name in enumerate(ethernet_interfaces):
                io.write('\r\n{}. {}'.format(idx, name).encode('utf-8'))
            io.write('\r\n> Enter interface number to configure (b to go back): '.encode('utf-8'))

            cmd = io_echo_read_until(io, b'\r').strip()
            if cmd == 'b':
                if hasChanged:
                    io.write('\r\n> Save and apply network configuration changes (yes or y): '.encode('utf-8'))
                    cmd = io_echo_read_until(io, b'\r').strip()
                    if cmd in {'y', 'yes'}:
                        io.write('\r\n> Network connectivity may be briefly interrupted'.encode('utf-8'))
                        io.write('\r\n> Saving and applying changes'.encode('utf-8'))
                        with open('/etc/netplan/01-network-manager-all.yaml', 'w') as f:
                            yaml.dump(netplan, f)
                        os.system('netplan apply')
                        break
                    else:
                        io.write('\r\nChanges discarded'.encode('utf-8'))
                        break
                else:
                    break
            try:
                idx = int(cmd)
                interface = ethernet_interfaces[idx]

                while True:
                    io.write('\r\n\r\n{}:'.format(interface).encode('utf-8'))
                    io.write('\r\n----------------------------------------'.encode('utf-8'))
                    io.write('\r\n0. Automatic (DHCP)'.encode('utf-8'))
                    io.write('\r\n1. Manual'.encode('utf-8'))
                    io.write('\r\n> Enter option number (b to go back): '.encode('utf-8'))

                    cmd = io_echo_read_until(io, b'\r').strip()
                    if cmd == 'b':
                        break
                    elif cmd == '0':
                        netplan['network']['ethernets'][interface] = {}
                        netplan['network']['ethernets'][interface] = { 'dhcp4': True }
                        hasChanged = True
                        break
                    elif cmd == '1':
                        ip = ''
                        nm = ''
                        gw = ''
                        n1 = ''
                        n2 = ''

                        while True:
                            io.write('\r\n> Enter static IP address (b to cancel) [required]: '.encode('utf-8'))
                            ip = io_echo_read_until(io, b'\r').strip()
                            if ip == 'b':
                                break
                            if ip == '':
                                continue

                            m = re.match('^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.){3}(25[0-5]|(2[0-4]|1\d|[1-9]|)\d)$', ip)
                            if m == None:
                                io.write('\r\nInvalid IP address'.encode('utf-8'))
                            else:
                                break
                        if ip == 'b':
                            break

                        while True:
                            io.write('\r\n> Enter netmask (b to cancel) [required]: '.encode('utf-8'))
                            nm = io_echo_read_until(io, b'\r').strip()
                            if nm == 'b':
                                break
                            if nm == '':
                                continue

                            m = re.match('^(255)\.(0|128|192|224|240|248|252|254|255)\.(0|128|192|224|240|248|252|254|255)\.(0|128|192|224|240|248|252|254|255)$', nm)
                            if m == None:
                                io.write('\r\nInvalid netmask'.encode('utf-8'))
                            else:
                                break
                        if nm == 'b':
                            break

                        while True:
                            io.write('\r\n> Enter gateway IP address (b to cancel) [optional]: '.encode('utf-8'))
                            gw = io_echo_read_until(io, b'\r').strip()
                            if gw == 'b':
                                break
                            if gw == '':
                                break

                            m = re.match('^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.){3}(25[0-5]|(2[0-4]|1\d|[1-9]|)\d)$', gw)
                            if m == None:
                                io.write('\r\nInvalid IP address'.encode('utf-8'))
                            else:
                                break
                        if gw == 'b':
                            break

                        while True:
                            io.write('\r\n> Enter nameserver 1 IP address (b to cancel) [optional]: '.encode('utf-8'))
                            n1 = io_echo_read_until(io, b'\r').strip()
                            if n1 == 'b':
                                break
                            if n1 == '':
                                break

                            m = re.match('^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.){3}(25[0-5]|(2[0-4]|1\d|[1-9]|)\d)$', n1)
                            if m == None:
                                io.write('\r\nInvalid IP address'.encode('utf-8'))
                            else:
                                break
                        if n1 == 'b':
                            break

                        while True:
                            io.write('\r\n> Enter nameserver 2 IP address (b to cancel) [optional]: '.encode('utf-8'))
                            n2 = io_echo_read_until(io, b'\r').strip()
                            if n2 == 'b':
                                break
                            if n2 == '':
                                break

                            m = re.match('^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.){3}(25[0-5]|(2[0-4]|1\d|[1-9]|)\d)$', n2)
                            if m == None:
                                io.write('\r\nInvalid IP address'.encode('utf-8'))
                            else:
                                break
                        if n2 == 'b':
                            break

                        ip += '/' + str(netmask_to_cidr(nm))
                        if 'ethernets' not in netplan['network']:
                            netplan['network']['ethernets'] = {}

                        netplan['network']['ethernets'][interface] = {}
                        netplan['network']['ethernets'][interface] = { 'addresses': [ip] }

                        if (len(gw)):
                            netplan['network']['ethernets'][interface].update({ 'routes': [{'to': 'default', 'via': gw }] })

                        ns = []
                        if (len(n1)):
                            ns.append(n1)
                        if (len(n2)):
                            ns.append(n2)

                        if (len(ns)):
                            netplan['network']['ethernets'][interface].update({ 'nameservers': {'addresses': ns } })
                        # print(yaml.dump(netplan))
                        hasChanged = True
                        break
                    else:
                        io.write('\r\n> Invalid option selection'.encode('utf-8'))

            except (ValueError, IndexError):
                io.write('\r\nInvalid option selection'.encode('utf-8'))
    except (ValueError, IndexError):
        io.write('\r\nInvalid option selection'.encode('utf-8'))


def do_factory_reset(io, args):
    io.write('\r\n> Please confirm factory reset (yes or y): '.encode('utf-8'))
    cmd = io_echo_read_until(io, b'\r').strip()
    if cmd in {'y', 'yes'}:
        io.write('\r\nRunning factory reset\r\n'.encode('utf-8'))
        subprocess.run('/home/opal/SDKVM/scripts/blackbox/restore.sh', shell=True, check=False, executable='/bin/bash')
        io.write('\r\nPlease reboot the system\r\n'.encode('utf-8'))
    else:
        io.write('\r\nFactory reset canceled'.encode('utf-8'))


main_menu = {
        r'help$|h$|\?$'        : print_help_main,
        r'reboot$'             : do_reboot,
        r'shutdown$'           : do_shutdown,
        r'start all$'          : do_start_all,
        r'start (vm[0-7])$'    : do_start_one,
        r'stop all$'           : do_stop_all,
        r'stop (vm[0-7])$'     : do_stop_one,
        r'print (vm[0-7])$'    : do_print_one,
        r'config (vm[0-7])$'   : do_config_one,
        r'print net$'          : do_print_net,
        r'config net$'         : do_config_net,
        r'factory reset$'      : do_factory_reset,
}

def lookup(cmd, re_dict):
    for exp in re_dict:
        m = re.match(exp, cmd)
        if m:
            return (re_dict[exp], m.groups())
    return (None, None)

def main() -> int:
    while True:
        try:
            with serial.Serial('/dev/ttyUSB0', 115200, bytesize=8, parity='N', stopbits=1, xonxoff=0, rtscts=0, dsrdtr=0) as io:
                sys.stdout.write('USB serial device opened and configured\r\n')
                while True:
                    io.write('\r\n> '.encode())
                    cmd = io_echo_read_until(io, b'\r').strip()
                    if (cmd != ''):
                        action, args = lookup(cmd, main_menu)
                        if action == None:
                            io.write('\r\nInvalid command. Enter help, h, or ? for a list of valid commands'.encode('utf-8'))
                        else:
                            action(io, args)
        except (serial.SerialException, serial.SerialTimeoutException):
            time.sleep(1)
    return 0

if __name__ == '__main__':
    sys.exit(main())
