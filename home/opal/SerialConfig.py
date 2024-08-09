#SerialConfig.py

import configparser
from datetime import datetime
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
import psutil


def find_writable_media():
    parts = psutil.disk_partitions()
    parts.sort(key=lambda _: _.mountpoint)
    for p in parts:
        if p.device.startswith('/dev/sd') and p.mountpoint.startswith('/media/'):
            for opt in p.opts.split(','):
                if opt == 'rw' or opt == 'w':
                    return p.mountpoint


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
    io.write('version                   Print Opal software version\r\n'.encode('utf-8'))
    io.write('get diag                  Retrieve diagnostics and write to external usb drive\r\n'.encode('utf-8'))
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
    config.optionxform=str
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

    gateways = netifaces.gateways()
    # call libsystem_cli --eth-interface to find correct interface
    command = f'sudo libsystem_cli --eth-interface'
    process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Get output and error messages
    output, error = process.communicate()

    if process.returncode != 0:
        print(f'Execution failed with error: {str(error)}')
    else:
        print('Successfully executed libsystem_cli --eth-interface')
        libsystem_cli_interface = (output).decode('utf-8')
        print(f'libsystem_cli_interface: {libsystem_cli_interface}')

    for interface in netifaces.interfaces():
        if str(interface) == (str((libsystem_cli_interface).rstrip("\n"))):
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

    ethernet_interfaces = []

    # call libsystem_cli --eth-interface to find correct interface
    command = f'sudo libsystem_cli --eth-interface'
    process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Get output and error messages
    output, error = process.communicate()

    if process.returncode != 0:
        print(f'Execution failed with error: {str(error)}')
    else:
        print('Successfully executed libsystem_cli --eth-interface')
        libsystem_cli_interface = (output).decode('utf-8')
        print(f'libsystem_cli_interface: {libsystem_cli_interface}')

    for interface in netifaces.interfaces():
        if str(interface) == (str((libsystem_cli_interface).rstrip("\n"))):
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


                        get_connection_name = f"nmcli -g name con"
                        connection_name_process = subprocess.Popen(get_connection_name, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        # Get output and error messages
                        output, error = connection_name_process.communicate()

                        #if connection_name_process.returncode != 0:
                        print(str(output))
                        connection_name_string = str(output, encoding='utf-8').rstrip('\n')
                        print(connection_name_string)

                        connection_name_string_with_breaks = connection_name_string.splitlines(keepends=True)
                        print(connection_name_string_with_breaks)
                        #syslog.syslog(syslog.LOG_INFO, f'connection_name_string with breaks: {connection_name_string_with_breaks}')

                        if len(connection_name_string_with_breaks) > 1:
                            for line in connection_name_string_with_breaks:
                                connection_name_string_line = line.rstrip('\n')
                                delete_existing_connection = f"nmcli connection delete id '{connection_name_string_line}'"

                                delete_existing_connection_process = subprocess.Popen(delete_existing_connection, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                                # Get output and error messages
                                output, error = delete_existing_connection_process.communicate()
                                print(str(output, encoding='utf-8').rstrip('\n'))
                        else:
                            delete_existing_connection = f"nmcli connection delete id '{connection_name_string}'"

                            delete_existing_connection_process = subprocess.Popen(delete_existing_connection, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                            # Get output and error messages
                            output, error = delete_existing_connection_process.communicate()
                            print(str(output, encoding='utf-8').rstrip('\n'))

                        subnet_mask_cidr = netmask_to_cidr(nm)

                        #command = f"nmcli con mod {connection_name_string} ipv4.address {ip_address}/{subnet_mask_cidr} ipv4.gateway {gateway} ipv4.dns '{dns} {backup_dns}'"

                        command = f"nmcli con add type ethernet con-name static-ip ifname '{interface}' ipv4.method manual ipv4.address '{ip}' gw4 '{gw}' ipv4.dns '{n1}, {n2}'"

                        nmcli_command_process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                        # Get output and error messages
                        output, error = nmcli_command_process.communicate()

                        #if nmcli_command_process.returncode == 0:
                        print(str(output, encoding='utf-8').rstrip('\n'))
                        #else:
                        print(str(error, encoding='utf-8').rstrip('\n'))

                        time.sleep(0.500)
                        print('250 milliseconds passed')
                        command = f"nmcli con up id static-ip"

                        nmcli_command_process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                        # Get output and error messages
                        output, error = nmcli_command_process.communicate()

                        #if nmcli_command_process.returncode == 0:
                        print(str(output, encoding='utf-8').rstrip('\n'))
                        #else:
                        print(str(error, encoding='utf-8').rstrip('\n'))

                        subprocess.run(f'/home/opal/gateway/generate_certificate_nginx.sh {ip} true', shell=True, check=False, executable='/bin/bash')

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
                    #io.write('\r\n0. Automatic (DHCP)'.encode('utf-8'))
                    io.write('\r\n0. Manual'.encode('utf-8'))
                    io.write('\r\n> Enter option number (b to go back): '.encode('utf-8'))

                    cmd = io_echo_read_until(io, b'\r').strip()
                    if cmd == 'b':
                        break
                    elif cmd == '0':
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

                        ns = []
                        if (len(n1)):
                            ns.append(n1)
                        if (len(n2)):
                            ns.append(n2)

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


def do_print_version(io, args):
    with open('/home/opal/VERSION', 'r') as f:
        version = f.readline().rstrip()
        io.write('\r\nVersion: {}'.format(version).encode('utf-8'))


def do_get_diag(io, args):
    path = find_writable_media()
    if path != None:
        io.write(f'\r\nFound writable media at {path}'.encode('utf-8'))
        time = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = f'{path}/emd3000gediag_{time}.zip'
        subprocess.run(f'/home/opal/SDKVM/scripts/blackbox/diagnostics.sh {path}', shell=True, check=False, executable='/bin/bash')
        os.sync()
        if (os.path.isfile(path)):
            io.write(f'\r\nDiagnostics written to: {path}'.encode('utf-8'))
        else:
            io.write(f'\r\nFailed to write diagnostics archive'.encode('utf-8'))
    else:
        io.write(f'\r\nNo writable media found. Please connect a USB storage device to Opal unit'.encode('utf-8'))


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
        r'version$'            : do_print_version,
        r'get diag$'           : do_get_diag,
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
