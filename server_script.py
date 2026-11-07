#!/usr/bin/python
# http://www.binarytides.com/python-socket-server-code-example/
import socket
import sys
import json
import os
import distutils.util
import subprocess
import time
from threading import Thread

HOST = ''   # Symbolic name meaning all available interfaces
PORT = 8888 # Arbitrary non-privileged port

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print('Socket created')

#Bind socket to local host and port
try:
    s.bind((HOST, PORT))
except socket.error as msg:
    print('Bind failed. Error Code : ' + str(msg) + ' Message ' + msg[1])
    sys.exit()

print('Socket bind complete')

#Start listening on socket
s.listen(10)
print('Socket now listening')

#Function for handling connections. This will be used to create threads
def clientthread(conn, addr):
    #Sending message to connected client

    #infinite loop so that function do not terminate and thread do not end.
    while True:

        reply = ""
        #Receiving from client
        data = conn.recv(1024)
        if not data:
            break
        if data == 'exit':
            break

        try:
            msg = json.loads(data)
            if 'restore' in msg:
                print("Restoring container source message: " + str(msg))
                os.system('criu -V')

                # down = True
                # while down:
                #     try:
                #         test_socket = socket.socket()
                #         test_socket.bind(('10.0.8.3',23456))
                #     except:
                #         continue
                #     down = False
                # print("container local IP 10.0.8.3 bound")
                try:
                    lazy = bool(distutils.util.strtobool(msg['restore']['lazy']))
                except:
                    lazy = False

                start = time.time()
                old_cwd = os.getcwd()
                os.chdir(msg['restore']['path'])
                cmd = 'runc restore -d --image-path ' + msg['restore']['image_path']
                cmd += ' --work-path ' + msg['restore']['image_path']
                cmd += ' --manage-cgroups-mode ignore'
                cmd += ' --tcp-established --ext-unix-sk --shell-job --file-locks --auto-dedup'
                if lazy:
                    cmd += ' --lazy-pages'
                cmd += ' ' + msg['restore']['name']
                print("Running " +  cmd)
                p = subprocess.Popen(cmd, shell=True)
                if lazy:
                    cmd = "criu lazy-pages -vv --page-server --address " + addr
                    cmd += " --port 27 -vv -D "
                    cmd += msg['restore']['image_path']
                    cmd += " -W "
                    cmd += msg['restore']['image_path']
                    print("Running lazy-pages server: " + cmd)
                    lp = subprocess.Popen(cmd, shell=True)
                ret = p.wait()
                end = time.time()
                if ret == 0:
                    reply = "runc restored %s successfully in  %.2f s" % (msg['restore']['name'], end - start)
                else:
                    reply = "runc failed(%d)" % ret
                os.chdir(old_cwd)
            elif 'take_ip' in msg:
                print("Taking over IP")
                os.unlink(msg['take_ip'])
                os.system('systemctl start keepalived')
                os.system('ip a')
            else:
                print("Unkown request : " + msg)
        except:
            continue

        print(reply)
        conn.sendall(reply.encode())
        conn.close()

    #came out of loop
    conn.close()

#now keep talking with the client
while 1:
    #wait to accept a connection - blocking call
    conn, addr = s.accept()
    print('Connected with ' + addr[0] + ':' + str(addr[1]))

    #start new thread takes 1st argument as a function name to be run, second is the tuple of arguments to the function.
    Thread(target=clientthread, args=(conn, str(addr[0]),)).start()

s.close()