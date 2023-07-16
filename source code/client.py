import socket
import time
import os
HEADER_SIZE = 4
SERVER_PORT = 69
DATA_SIZE = 512
BLK_SIZE = HEADER_SIZE + DATA_SIZE
BUFFER_SIZE = 600

"""
Dictionary mapping TFTP opcodes (operation codes) to their corresponding numerical values
"""
OPCODES = {
    'read': 1, # RRQ
    'write': 2, # WRQ
    'data': 3, # DATA
    'ack': 4, # ACK
    'error': 5 # ERROR
}

"""
Dictionary mapping TFTP transfer modes to their corresponding numerical values
RFC 1350 specifies two modes: netascii and octet
"""
MODES = {
    'netascii': 1,
    'octet': 2
}

"""
    Construct and send a TFTP request packet to a TFTP server.

    Parameters:
        operation (str): The type of TFTP operation ('read' for RRQ or 'write' for WRQ).
        filename (str): The name of the file being requested or written.
        mode (str): The transfer mode for the file ('netascii' or 'octet').
        server (tuple): The server's address (IP address and port) where the request packet will be sent.

    Description:
        This function creates a TFTP request packet using a bytearray and sends it to the server using a socket.
        The TFTP request packet consists of the following format:
            - 2 bytes: Opcode representing the TFTP operation (RRQ or WRQ).
            - n bytes: Filename (encoded in UTF-8) of the file being requested or written.
            - 1 byte: Null terminator to terminate the filename field.
            - n bytes: Transfer mode (encoded in UTF-8) for the file transfer (netascii or octet).
            - 1 byte: Null terminator to terminate the mode field.
    """

def tftp_create_req(operation, filename, mode, server):
    
    request = bytearray()

    # 01 for RRQ, 02 for WRQ
    request.append(0)
    request.append(OPCODES[operation])

    # Null terminator after the filename
    filename = bytearray(filename.encode('utf-8'))
    request += filename
    request.append(0)

    # Transfer mode
    mode = bytearray(bytes(mode, 'utf-8')) 
    request += mode

    # Null terminator at the end
    request.append(0) 
    
    # Send request to the server
    sock.sendto(request, server) 
    print(f"Request: {request}")


"""
    Send a TFTP acknowledgment packet (ACK) to a TFTP client.

    Parameters:
        ack_data (bytes): The ACK data containing the block number from the client.
        server (tuple): The client's address (IP address and port) to send the ACK packet.
    """

def tftp_send_ack(ack_data, server):
    ack = bytearray(ack_data)

    # 04 for ACK
    ack[0] = 0
    ack[1] = OPCODES['ack']

    #print(f"Ack packet: {ack}\n")
    sock.sendto(ack, server)

"""
    Perform TFTP read operation to download a file from a TFTP server.

    Parameters:
        filename_saved (str): The name of the file to be saved after downloading.
        mode (str): The transfer mode for the file ('netascii' or 'octet').

    Description:
        This function performs a TFTP read operation to download a file from a TFTP server.
        It opens the specified file in the given mode ('netascii' or 'octet') for writing the downloaded data.

        The TFTP read operation involves the following steps:
        - Waiting for incoming data packets (DATA) from the server using a socket with a timeout of 5 seconds.
        - Handling socket timeouts, indicating server unresponsiveness during the read operation.
        - Checking for server errors using the `error_detection()` function and stopping the operation if an error is received.
        - Writing the received data to the file, handling any disk full errors that may occur.
        - Sending acknowledgment packets (ACK) for received data to the server using the `tftp_send_ack()` function.
        - Repeating the process until the last data packet is received, which indicates the successful download of the file.

    """

def read(filename_saved, mode):
    if mode == 'netascii':
        file = open(filename_saved, "w") 
    elif mode == 'octet':
        file = open(filename_saved, "wb")
      
    while True:
        sock.settimeout(5)
        try:
            data, server = sock.recvfrom(BUFFER_SIZE)  
        except socket.timeout:
            print('[Timeout!! server is not responsive!]')
            print('[Terminating!!]\n')
            break
        if error_detection(data):
            break

        cont = data[4:]
        #print(f"Content : {cont}")

        if mode == 'netascii':
            cont = cont.decode("utf-8")

        try:
            file.write(cont)
        except OSError:
            print(errors[3]) #handles the disk full errors
            break

        #print(f"[Data]: {data[0:4]} : {len(data)}")

        tftp_send_ack(data[0:4], server)
        #last DATA packet
        if len(data) < BLK_SIZE:
            print('[File downloaded successfully!]\n')
            break

    file.close()


""" 
    Perform TFTP write operation to upload a file to a TFTP server.

    Parameters:
        filename (str): The name of the file to be uploaded.
        mode (str): The transfer mode for the file ('netascii' or 'octet').

    Description:
        It opens the specified file in the given mode ('netascii' or 'octet') based on the mode parameter.

        The TFTP write operation involves the following steps:
        - Sending the initial WRQ (Write Request) packet to the server, requesting to write the specified file.
        - Receiving acknowledgment packets from the server for each block of data sent.
        - Handling duplicate ACKs (Acknowledgments) to avoid retransmission of the same block.
        - Reading blocks of data from the file and sending them to the server as DATA packets.
        - Receiving the final ACK packet from the server to indicate successful file upload.

    """

def write(filename, mode):
    if mode == 'netascii':
        file = open(filename, "r")
    elif mode == 'octet':
        file = open(filename, "rb")

    prev_blockno = -1

    while True:
        sock.settimeout(5)
        try:
            ack, server = sock.recvfrom(BUFFER_SIZE) #waiting response
        except socket.timeout:
            print('[Timeout!! server is not responsive!]')
            print('[Terminating!!]\n')
            break

        if error_detection(ack):
            break 
        # Duplicate ACK handling
        if prev_blockno != int.from_bytes(ack[2:4], byteorder='big'):

            #print(f"Ack packet: {ack}")

            block_no = int.from_bytes(ack[2:4], byteorder='big')
            prev_blockno = block_no
            block_no = block_no + 1

            # Reading files as data and should be <512 
            data = file.read(512)
            #print(f"Content : {data}")

            if mode == 'netascii':
               
                data = bytearray(bytes(data, 'utf-8'))
            data_packet(block_no, data, server)
            
            if len(data) < DATA_SIZE:
                # Waiting for last ACK response 
                ack, server = sock.recvfrom(BUFFER_SIZE)
                print('File uploaded successfully.\n')
                break

    file.close()

"""
    Send a TFTP data packet (DATA) to a TFTP client.

    Parameters:
        block_no (int): The block number of the data packet being sent.
        data (bytearray): The data to be included in the DATA packet.
        server (tuple): The client's address (IP address and port) to send the DATA packet.
    """

def data_packet(block_no, data, server):
    d_packet = bytearray()
    #03 for DATA
    d_packet.append(0)
    d_packet.append(OPCODES['data'])
  
    d_packet.append(0)
    d_packet.append(block_no)
    d_packet += data

    sock.sendto(d_packet, server)
    #print(f"[Data]: {d_packet[0:4]} : {len(d_packet)}\n")

# TFTP error codes and their corresponding error messages as defined in RFC 1350 version 2
errors = {
    0: "Not defined, see error message (if any).",
    1: "File not found.",
    2: "Access violation.",
    3: "Disk full or allocation exceeded.",
    4: "Illegal TFTP operation.",
    5: "Unknown transfer ID.",
    6: "File already exists.",
    7: "No such user."
} 

"""
    Send a TFTP error packet (ERROR) to a TFTP client.

    Parameters:
        error_code (int): The TFTP error code representing the type of error.
        server (tuple): The client's address (IP address and port) to send the ERROR packet.

"""
def error_packet(error_code, server):
    err = bytearray()

    err.append(0)
    err.append(OPCODES['error'])

    err.append(0)
    err.append(error_code)

    errMsg = errors[error_code]
    errMsg = bytearray(errMsg.encode('utf-8'))
    err += errMsg

    err.append(0)

    sock.sendto(err, server)
    print(f"Error {err}")

"""
    Check if a TFTP server response contains an error packet (ERROR).

    Parameters:
        server_response (bytes): The response received from the TFTP server.

    Returns:
        bool: True if the response contains an error packet, False otherwise.

    Description:
        If an error packet is found, the function prints the corresponding error message and terminates.
        It returns True if an error packet is present, and False otherwise.

"""

def error_detection(server_response):
    opcode = server_response[:2]
    err = (int.from_bytes(opcode, byteorder='big') == OPCODES['error'])

    if err:
        error_code = int.from_bytes(
            server_response[2:4], byteorder='big')     
        print('Error raised: ' + errors[error_code])
        print('Terminating...\n')

    return err

"""
    Check if a file exists on the local file system.

    Parameters:
        filename (str): The name of the file to be checked.

    Returns:
        int: 1 if the file exists, 0 if the file does not exist.

"""
def valid_file(filename):
    try:
        file = open(filename)
        file.close()
        return 1
    except IOError:
        return 0

"""
    Print successful connection message to a TFTP server.

    Parameters:
        server_ip (str): The IP address of the TFTP server.

"""
def connection(server_ip): 
        print('  ._._._._._._._._._._._._._._._._._.')
        print('\n  Successfully connected to ' + server_ip)

  


def main():
    print('  ._._._._._._._._._._._._._._._._._.')
    print('  |  _______ ______ _______ _____   |')
    print('  | |__   __|  ____|__   __|  __ \  |')
    print('  |    | |  | |__     | |  | |__) | |')
    print('  |    | |  |  __|    | |  |  ___/  |')
    print('  |    | |  | |       | |  | |      |')
    print('  |    |_|  |_|       |_|  |_|      |')
    print('  ._._._._._._._._._._._._._._._._._.')
    print('\n')
    time.sleep(1)
    server_ip = input('  Enter IP address of TFTP server: ') 
    print('  ...Connecting to host ' + server_ip + '...')
    server = (server_ip, SERVER_PORT)
    print('\n')

    time.sleep(1)
    connection(server_ip)


    while True:

        try:

            print('\n  COMMANDS:')
            print('    TFTP Operation CODES:')
            print('      [1] GET (Download)')
            print('      [2] PUT (Upload)')
            print('      [3] Exit')

            operation = input('Enter command: ')

            if operation == '3':
                print('Exiting Client...')
                break

            print('    TFTP Transfer FILENAME Format:')
            print('      Ex. "Sample.jpg"')
            print('\n')

            filename = input('Enter filename: ')

            _, file_extension = os.path.splitext(filename)

            # Check if the file extension is in the list of image extensions
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
            if file_extension.lower() in image_extensions:
                mode = 'octet'  # If it's an image, set mode to 'octet'
            else:
                print('    TFTP Transfer MODES:')
                print('    [1] "netascii" [2] "octet"')
                print('\n')

                mode = input('Enter mode: ')
                if mode == '1':
                    mode = 'netascii'
                elif mode == '2':
                    mode = 'octet'


            operation = operation.lower()
            mode = mode.lower()
            # Sends RRQ and WRQ packets to the server
            if mode in MODES:
                if operation == '1':
                    filename_saved = input(
                        'Enter new filename: ')
                    tftp_create_req('read', filename, mode, server)
                    read(filename_saved, mode)

                elif operation == '2':
                    if valid_file(filename):
                        tftp_create_req('write', filename, mode, server)
                        write(filename, mode)
                    else:

                        print('[File not found || access violation]\n')

                else:
                    print('-- Invalid Command --\n')
            else:
                print('-- Invalid Mode --\n')

        except ValueError:
            print('-- Invalid Input --\n')
        except ConnectionError:
            print('-- Server Unresponsive --\n')

#Creates UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)    
main()
sock.close()
