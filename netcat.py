import sys
import socket
import getopt
import threading
import subprocess
import argparse

#define some global variables
listen              = False
command             = False
upload              = None
execute             = None
target              = None
upload_destination  = None
port                = None


# def usage():
#     print("BHP Net Tool")
#     print()
#     print("Usage: bhpnet.py -t target_host -p port")
#     print("-l --listen                  - listen on [host] : [port] for incoming connections")
#     print("-e --execute=file_to_run     - execute the given file upon receiving a connection")
#     print("-c --command                 - initialize a command shell")
#     print("-u --upload=destination      - upon receiving connection upload a file and write to [destination]")
#     print()
#     print()
#     print("Examples: ")
#     print("bhpnet.py -t 192.168.0.1 -p 5555 -l -c")
#     print("bhpnet.py -t 192.168.0.1 -p 5555 -l -u=c:\\target.exe")
#     print("bhpnet.py -t 192.168.0.1 -p 5555 -l -e=\"cat /etc/passwd\"")
#     print("echo 'ABCDEFGHI' | ./bhpnet.py -t 192.168.11.12 -p 135")
#     sys.exit(0)

def client_sender(buffer):
    print("DBG: sending data to client on port " + str(port))

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        #connect to our target host
        client.connect((target, port))

        if len(buffer):
            client.send(buffer.encode())

        while True:
            #now wait for data back
            recv_len = 1
            response = ''

            while recv_len:
                print("DBG: waiting for response from client")

                data = client.recv(4096)
                recv_len = len(data)
                response += data.decode(errors="ignore")

                if recv_len < 4096:
                    break

            print(response, end="")
            #wait for more input
            buffer = input("")
            buffer += "\n"

            #send it off
            client.send(buffer.encode())

    except:
        print("[*] Exception! Exiting.")
    
    finally:
        #tear down the connection
        client.close


def server_loop():
    global target
    print("DBG: entering server loop")

    #if no target is defined, we listen on all  interfaces
    # if not len(target):
    #     target = "0.0.0.0"

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((target, port))
    server.listen(5)

    while True:
        client_socket, addr = server.accept()

        #spin off a thread to handle our new client
        client_thread = threading.Thread(target=client_handler, args=(client_socket,))
        client_thread.start()

def run_command(command):
    #trim the newline
    command = command.rstrip()
    print("DBG: executing command: " + command)

    #run the command and get the output back
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
    except:
        output = "Failed to execute command.\r\n"

    #send the output back to the client
    return output

def client_handler(client_socket):
    global upload
    global execute
    global command

    #check for upload
    if upload_destination is not None:
        print("DBG: entering file upload")

        #read in all of the bytes and write to our destination
        file_buffer = ""

        #keep reading data until none is available
        while True:
            data = client_socket.recv(1024)

            if not data:
                break
            else:
                file_buffer += data.decode()

        #now we take these bytes and try to write them out
        try:
            file_descriptor = open(upload_destination, "wb")
            file_descriptor.write(file_buffer)
            file_descriptor.close()

            #acknowledge that we wrote the file out
            client.send("Succesfully saved file to {0} \r\n".format(upload_destination)).encode()
        
        except:
            client_socket.send("Failed to save fileto {0}\r\n".format(upload_destination)).encode()

    if execute is not None:
        print("DBG: going to execute command")

        #run the command
        output = run_command(execute)
        client_socket.send(output.encode())
    
    #now we go into another shell if a command shell was requested
    if command:
        print("DBG: shell requested")
        #show a simple prompt
        client_socket.send("<BHP:#> ".encode())

        while True:
            
            #now we receive until we see a linefeed(enter key)
            cmd_buffer = ""
            while "\n" not in cmd_buffer:
                cmd_buffer += client_socket.recv(1024).decode()

            #send back the command output
            response = run_command(cmd_buffer)

            if isinstance(response, str):
                response = response.encode()

            #send back the response
            client_socket.send(response + "<BHP:#> ".encode())

def main():
    global listen
    global port
    global execute
    global command
    global upload_destination
    global target
    
    # if not len(sys.argv[1:]):
    #     usage()

    #setup argument parsing
    # try:
    parser = argparse.ArgumentParser(description="Simple netcat clone.")
    parser.add_argument("-p", "--port", type=int, help="target port")
    parser.add_argument("-t", "--target", type=str, help="target host", default="0.0.0.0")
    parser.add_argument("-l", "--listen", help="listen on [host]:[port] for incoming connections", action="store_true", default=False)
    parser.add_argument("-e", "--execute", help="--execute=file_to_run execute the given file upon receiving a connection")
    parser.add_argument("-c", "--command", help="initialize a command shell", action="store_true", default=False)
    parser.add_argument("-u", "--upload", help="--upload=destination upon receiving connection upload a file and write to [destination]")
    args = parser.parse_args()

    #parse arguments
    target = args.target
    port = args.port
    listen = args.listen
    execute = args.execute
    command = args.command
    upload_destination = args.upload


    # except:
    #     usage()

    #are we going to listen or just send data from stdin?
    if not listen and target is not None and port > 0:
        print("DBG: read data from stdin")
        #read data from stdin, this will block so send CTRL-D if not sending to stdin

        buffer = input("#: ")
        
        print("Sending {0} to client".format(buffer))
        #send data off
        client_sender(buffer)

    #we are going to listen and potentially upload things, execute commands, and drop a shell back
    #depending on our command line options above

    if listen:
        server_loop()


main()
