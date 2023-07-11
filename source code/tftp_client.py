import socket
import struct
import sys
import os

# TFTP opcodes
OPCODE_RRQ = 1
OPCODE_WRQ = 2
OPCODE_DATA = 3
OPCODE_ACK = 4
OPCODE_ERROR = 5

# TFTP error codes
ERROR_FILE_NOT_FOUND = 1
ERROR_ACCESS_VIOLATION = 2
ERROR_DISK_FULL = 3

# TFTP packet size
PACKET_SIZE = 512

def create_rrq_packet(filename):
    return struct.pack('!H{}sB5sB'.format(len(filename)), OPCODE_RRQ, filename.encode(), 0, b'octet', 0)

def create_wrq_packet(filename):
    return struct.pack('!H{}sB5sB'.format(len(filename)), OPCODE_WRQ, filename.encode(), 0, b'octet', 0)

def create_data_packet(block_num, data):
    return struct.pack('!HH{}s'.format(len(data)), OPCODE_DATA, block_num, data)

def create_ack_packet(block_num):
    return struct.pack('!HH', OPCODE_ACK, block_num)

def create_error_packet(error_code, error_msg):
    return struct.pack('!H{}sB{}sB'.format(len(error_msg)), OPCODE_ERROR, error_code, error_msg.encode(), 0)

def parse_packet(packet):
    opcode = struct.unpack('!H', packet[:2])[0]
    if opcode == OPCODE_DATA:
        block_num = struct.unpack('!H', packet[2:4])[0]
        data = packet[4:]
        return opcode, block_num, data
    elif opcode == OPCODE_ACK:
        block_num = struct.unpack('!H', packet[2:4])[0]
        return opcode, block_num
    elif opcode == OPCODE_ERROR:
        error_code = struct.unpack('!H', packet[2:4])[0]
        error_msg = packet[4:-1].decode()
        return opcode, error_code, error_msg
    else:
        return opcode,

def send_receive_tftp_packet(sock, packet, server_address):
    sock.sendto(packet, server_address)
    response, address = sock.recvfrom(PACKET_SIZE)
    return response, address

def download_file(sock, server_address, filename):
    try:
        file = open(filename, 'wb')
        block_num = 1

        # Send the read request packet
        rrq_packet = create_rrq_packet(filename)
        sock.sendto(rrq_packet, server_address)

        while True:
            response, address = sock.recvfrom(PACKET_SIZE)
            opcode, *params = parse_packet(response)
            if opcode == OPCODE_DATA:
                received_block_num, data = params
                if received_block_num == block_num:
                    file.write(data)
                    ack_packet = create_ack_packet(block_num)
                    sock.sendto(ack_packet, address)
                    block_num += 1
                    if len(data) < PACKET_SIZE:
                        break
                else:
                    sock.sendto(ack_packet, address)  # Send duplicate ACK
            elif opcode == OPCODE_ERROR:
                error_code, error_msg = params
                print(f"Error: {error_code} - {error_msg}")
                break

        file.close()
        print(f"File downloaded successfully as '{filename}'")
    except IOError as e:
        print(f"Error: {e}")

def upload_file(sock, server_address, filename):
    try:
        file = open(filename, 'rb')
        block_num = 1

        # Send the write request packet
        wrq_packet = create_wrq_packet(filename)
        sock.sendto(wrq_packet, server_address)

        while True:
            data = file.read(PACKET_SIZE)
            if not data:
                break

            data_packet = create_data_packet(block_num, data)
            sock.sendto(data_packet, server_address)

            while True:
                response, address = sock.recvfrom(PACKET_SIZE)
                opcode, received_block_num = parse_packet(response)
                if opcode == OPCODE_ACK and received_block_num == block_num:
                    block_num += 1
                    break
                elif opcode == OPCODE_ERROR:
                    error_code, error_msg = params
                    print(f"Error: {error_code} - {error_msg}")
                    return

        file.close()
        print(f"File uploaded successfully as '{filename}'")
    except IOError as e:
        print(f"Error: {e}")

def tftp_client():
    server_ip = input("Enter the server IP address: ")
    server_port = 69  # TFTP default port
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        print("1. Upload file")
        print("2. Download file")
        print("3. Exit")
        choice = input("Enter your choice: ")

        if choice == '1':
            filename = input("Enter the filename to upload: ")
            upload_file(sock, (server_ip, server_port), filename)
        elif choice == '2':
            filename = input("Enter the filename to download: ")
            download_file(sock, (server_ip, server_port), filename)
        elif choice == '3':
            break
        else:
            print("Invalid choice. Please try again.")

    sock.close()

if __name__ == '__main__':
    tftp_client()
