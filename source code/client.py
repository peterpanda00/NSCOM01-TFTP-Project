import socket
import struct
import sys

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

# TFTP block size
BLOCK_SIZE = 512

def send_rrq(filename, server_ip, server_port, save_filename):
    # Create socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Pack RRQ packet
    rrq_packet = struct.pack('!H', OPCODE_RRQ)
    rrq_packet += filename.encode() + b'\0' + b'octet' + b'\0'
    
    # Send RRQ packet
    client_socket.sendto(rrq_packet, (server_ip, server_port))
    
    # Create or open the file for writing
    try:
        file = open(save_filename, 'wb')
    except IOError as e:
        print("Error: Failed to create file:", e)
        sys.exit(1)
    
    while True:
        # Receive data packet
        data_packet, server_address = client_socket.recvfrom(BLOCK_SIZE + 4)
        
        opcode = struct.unpack('!H', data_packet[:2])[0]
        block_number = struct.unpack('!H', data_packet[2:4])[0]
        
        if opcode == OPCODE_ERROR:
            error_code = struct.unpack('!H', data_packet[2:4])[0]
            error_message = data_packet[4:].decode()
            
            if error_code == ERROR_FILE_NOT_FOUND:
                print("Error: File not found on the server.")
            elif error_code == ERROR_ACCESS_VIOLATION:
                print("Error: Access violation.")
            elif error_code == ERROR_DISK_FULL:
                print("Error: Disk full.")
            
            file.close()
            sys.exit(1)
        
        if opcode == OPCODE_DATA:
            if block_number == 1:
                print("Downloading", save_filename)
            
            # Write data to file
            file.write(data_packet[4:])
            
            # Send ACK packet
            ack_packet = struct.pack('!H', OPCODE_ACK) + struct.pack('!H', block_number)
            client_socket.sendto(ack_packet, server_address)
            
            if len(data_packet) < BLOCK_SIZE + 4:
                break
    
    print("Download complete.")
    file.close()

def send_wrq(filename, server_ip, server_port):
    # Create socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Pack WRQ packet
    wrq_packet = struct.pack('!H', OPCODE_WRQ)
    wrq_packet += filename.encode() + b'\0' + b'octet' + b'\0'
    
    # Send WRQ packet
    client_socket.sendto(wrq_packet, (server_ip, server_port))
    
    # Open the file for reading
    try:
        file = open(filename, 'rb')
    except IOError as e:
        print("Error: Failed to open file:", e)
        sys.exit(1)
    
    block_number = 0
    while True:
        block_number += 1
        data = file.read(BLOCK_SIZE)
        
        if len(data) < BLOCK_SIZE:
            # Last data block
            packet = struct.pack('!H', OPCODE_DATA) + struct.pack('!H', block_number) + data
            client_socket.sendto(packet, (server_ip, server_port))
            
            break
        
        # Send data packet
        packet = struct.pack('!H', OPCODE_DATA) + struct.pack('!H', block_number) + data
        client_socket.sendto(packet, (server_ip, server_port))
        
        # Wait for ACK packet
        try:
            ack_packet, server_address = client_socket.recvfrom(4)
        except socket.timeout:
            print("Error: Server did not respond.")
            file.close()
            sys.exit(1)
        
        ack_opcode = struct.unpack('!H', ack_packet[:2])[0]
        ack_block_number = struct.unpack('!H', ack_packet[2:4])[0]
        
        if ack_opcode != OPCODE_ACK or ack_block_number != block_number:
            print("Error: Duplicate ACK received.")
            file.close()
            sys.exit(1)
    
    print("Upload complete.")
    file.close()

def main():
    # Get user input
    command = input("Enter 'upload' or 'download': ")
    
    if command == "upload":
        filename = input("Enter the filename to upload: ")
        server_ip = input("Enter the server IP address: ")
        server_port = int(input("Enter the server port number: "))
        
        send_wrq(filename, server_ip, server_port)
    elif command == "download":
        filename = input("Enter the filename to download: ")
        save_filename = input("Enter the filename to save the downloaded file as: ")
        server_ip = input("Enter the server IP address: ")
        server_port = int(input("Enter the server port number: "))
        
        send_rrq(filename, server_ip, server_port, save_filename)
    else:
        print("Invalid command.")

if __name__ == '__main__':
    main()
