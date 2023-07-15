import socket
import tkinter as tk
from tkinter import filedialog
HEADER_SIZE = 4
SERVER_PORT = 69
DATA_SIZE = 512
BLK_SIZE = HEADER_SIZE + DATA_SIZE
BUFFER_SIZE = 600

"""
    this function demonsrates how to construct a packet using bytearray
"""
OPCODES = {
    'read': 1, # RRQ
    'write': 2, # WRQ
    'data': 3, # DATA
    'ack': 4, # ACK
    'error': 5 # ERROR
}
# RFC 1350
MODES = {
    'netascii': 1,
    'octet': 2
}


def tftp_request(operation, filename, mode, server):
    """
    this function demonsrates how to construct a packet using bytearray
    """
    rqst = bytearray()

    # 01 for RRQ
    # 02 for WRQ
    rqst.append(0)
    rqst.append(OPCODES[operation])

    filename = bytearray(filename.encode('utf-8'))
    rqst += filename
    rqst.append(0) # appending null terminator

    mode = bytearray(bytes(mode, 'utf-8')) # appending mode of transfer
    rqst += mode

    rqst.append(0) # appending the last byte
    sock.sendto(rqst, server) # send request to server    
    print(f"Request: {rqst}")

def tftp_send_ack(ack_data, server):
    ack = bytearray(ack_data)

    # 04 for ACK
    ack[0] = 0
    ack[1] = OPCODES['ack']

    print(f"Ack packet: {ack}\n")
    sock.sendto(ack, server)

def tftp_read(filename_saved, mode):
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
        if tftp_server_error(data):
            break

        cont = data[4:]
        print(f"Content : {cont}")

        if mode == 'netascii':
            cont = cont.decode("utf-8")

        try:
            file.write(cont)
        except OSError:
            print(errors[3]) #handles the disk full errors
            break

        print(f"[Data]: {data[0:4]} : {len(data)}")

        tftp_send_ack(data[0:4], server)
        #last DATA packet
        if len(data) < BLK_SIZE:
            print('[File downloaded successfully!]\n')
            break

    file.close()


def tftp_write(filename, mode):
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

        if tftp_server_error(ack):
            break #stop
        # duplicate ACK handling
        if prev_blockno != int.from_bytes(ack[2:4], byteorder='big'):

            print(f"Ack packet: {ack}")

            block_no = int.from_bytes(ack[2:4], byteorder='big')
            prev_blockno = block_no
            block_no = block_no + 1

            #reading files as data and should be <512 
            data = file.read(512)
            print(f"Content : {data}")

            if mode == 'netascii':
                # converting data
                data = bytearray(bytes(data, 'utf-8'))
            tftp_send_data(block_no, data, server)
            # represents the last DATA packet
            if len(data) < DATA_SIZE:
                # waiting for last ACK response 
                ack, server = sock.recvfrom(BUFFER_SIZE)
                print('File uploaded successfully.\n')
                break

    file.close()


def tftp_send_data(block_no, data, server):
    d_packet = bytearray()
    #03 for DATA
    d_packet.append(0)
    d_packet.append(OPCODES['data'])
  
    d_packet.append(0)
    d_packet.append(block_no)
    d_packet += data

    sock.sendto(d_packet, server)
    print(f"[Data]: {d_packet[0:4]} : {len(d_packet)}\n")

# mentioned in RFC 1350 version 2
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


def tftp_send_error(error_code, server):
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



def tftp_server_error(server_response):
    opcode = server_response[:2]
    err = (int.from_bytes(opcode, byteorder='big') == OPCODES['error'])

    if err:
        error_code = int.from_bytes(
            server_response[2:4], byteorder='big')     
        print('Error raised: ' + errors[error_code])
        print('Terminating...\n')

    return err

#checking if the file exists 
def existing_file(filename):
    try:
        file = open(filename)
        file.close()
        return 1
    except IOError:
        return 0


def connect_to_server():
    server_ip = ip_entry.get()
    status_label.config(text='[Connecting to host ' + server_ip + '...]')

def browse_file():
    filename = filedialog.askopenfilename()
    filename_entry.delete(0, tk.END)
    filename_entry.insert(0, filename)

def submit_command():
    operation = operation_var.get().lower()
    filename = filename_entry.get()
    mode = mode_var.get().lower()

    if operation == 'exit' and filename == 'exit' and mode == 'exit':
        status_label.config(text='Exiting Client...')
        return

    operation = operation.lower()
    mode = mode.lower()

    if mode in MODES:
        if operation == 'get':
            filename_saved = alternate_filename_entry.get()
            status_label.config(text='Downloading file: ' + filename)
            tftp_request('read', filename, mode)
            tftp_read(filename_saved, mode)
            downloaded_filename_entry.delete(0, tk.END)
            downloaded_filename_entry.insert(0, filename_saved)
        elif operation == 'put':
            if existing_file(filename):
                status_label.config(text='Sending file: ' + filename)
                tftp_request('write', filename, mode)
                tftp_write(filename, mode)
            else:
                status_label.config(text='[File not found || access violation]\n')
        else:
            status_label.config(text='[Invalid Operation]\n')
    else:
        status_label.config(text='[Invalid Mode]\n')



window = tk.Tk()
window.geometry('500x500')
window.title('TFTP Client')


header_label = tk.Label(window, text='Input Server Address')
header_label.pack()


ip_label = tk.Label(window, text='IP Address:')
ip_label.pack()
ip_entry = tk.Entry(window)
ip_entry.pack()


connect_button = tk.Button(window, text='Connect', command=connect_to_server)
connect_button.pack()



operation_var = tk.StringVar()
upload_button = tk.Radiobutton(window, text='Upload', variable=operation_var, value='put')
upload_button.pack()
download_button = tk.Radiobutton(window, text='Download', variable=operation_var, value='get')
download_button.pack()


filename_label = tk.Label(window, text='Filename:')
filename_label.pack()
filename_entry = tk.Entry(window)
filename_entry.pack()
browse_button = tk.Button(window, text='Browse', command=browse_file)
browse_button.pack()


alternate_filename_label = tk.Label(window, text='Alternate Filename:')
alternate_filename_label.pack()
alternate_filename_entry = tk.Entry(window)
alternate_filename_entry.pack()

# Mode Dropdown
mode_label = tk.Label(window, text='Mode:')
mode_label.pack()
mode_var = tk.StringVar()
mode_dropdown = tk.OptionMenu(window, mode_var, *MODES)
mode_dropdown.pack()

# Submit Button
submit_button = tk.Button(window, text='Submit', command=submit_command)
submit_button.pack()

# Status Label
status_label = tk.Label(window, text='')
status_label.pack()


"""
    

def main():
    server_ip = input('Enter IP address of TFTP server: ')
    print('[Connecting to host ' + server_ip + '...]')
    server = (server_ip, SERVER_PORT)

    tftp_instruction(server_ip)

    while True:

        try:
            operation, filename, mode = input('Enter command: ').split()

            if operation == 'exit' and filename == 'exit' and mode == 'exit':
                print('Exiting Client...')
                break

            operation = operation.lower()
            mode = mode.lower()
            # for sending RRQ and WRQ packets to the server
            if mode in MODES:
                if operation == 'get':
                    filename_saved = input(
                        'Enter the filename to save the downloaded file: ')
                    tftp_request('read', filename, mode, server)
                    tftp_read(filename_saved, mode)

                elif operation == 'put':
                    if existing_file(filename):
                        tftp_request('write', filename, mode, server)
                        tftp_write(filename, mode)
                    else:
                        print('[File not found || access violation]\n')

                else:
                    print('[Invalid Operation]\n')
            else:
                print('[Invalid Mode]\n')

        except ValueError:
            print('[Invalid Input]\n')

"""
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)    #creating UDP socket
window.mainloop()
#closing UDP socket
sock.close()
