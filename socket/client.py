# Using Sliding Window
from threading import Thread
import socket
import bisect

ue_id = 1
host_mn = "127.0.0.1" #127.0.0.1 192.168.1.2
port_mn = 20001
host_sn = "192.168.0.153" #區網ip cmd Ipv4 192.168.1.3 192.168.1.114
port_sn = 20001
BUFFER_SIZE = 1000

class GlobalParameters():
    loss_packet_amount = 0
    packet_num = 10000000
    packet_seq_list = []
    had_count_loss_seq = 0
    window_size = 1000

class SocketClient(Thread):
    def __init__(self, host, port):
        super().__init__()
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Test Only
        if host == "192.168.1.3": ##host_sn
            self.client_socket.bind(("192.168.1.3", 50001)) ##host_sn
        ###
        self.client_socket.connect((host, port))
        self.client_socket.send(str(ue_id).encode("utf-8"))

    def run(self):
        self.wait_response()

    def wait_response(self):
        keep_going = True
        while keep_going:
            data_byte = self.client_socket.recv(BUFFER_SIZE)
            data = bytes.decode(data_byte)

            seq_index = data.find("seq:")
            if seq_index != -1:
                try:
                    seq = int(data[seq_index + 4:seq_index + 14])
                    bisect.insort(GlobalParameters.packet_seq_list, seq)

                    while len(GlobalParameters.packet_seq_list) >= 2 and GlobalParameters.packet_seq_list[1] - GlobalParameters.packet_seq_list[0] == 1:
                        del GlobalParameters.packet_seq_list[0]
                    
                    if len(GlobalParameters.packet_seq_list) > GlobalParameters.window_size:
                        if GlobalParameters.packet_seq_list[0] >= GlobalParameters.had_count_loss_seq:
                            GlobalParameters.loss_packet_amount += (GlobalParameters.packet_seq_list[1] - GlobalParameters.packet_seq_list[0] - 1)
                            GlobalParameters.had_count_loss_seq = GlobalParameters.packet_seq_list[1]
                        del GlobalParameters.packet_seq_list[0]

                except:
                    print("Packet Error")


if __name__ == '__main__':

    client_mn = SocketClient(host_mn, port_mn)
    client_sn = SocketClient(host_sn, port_sn)
    client_mn.setDaemon(True)
    client_sn.setDaemon(True)
    client_mn.start()
    client_sn.start()

    while True:
        command = input()
        if command == "end":
            break


    if len(GlobalParameters.packet_seq_list) > 0:
        check_start_seq = GlobalParameters.packet_seq_list[0]
    for i in range(check_start_seq, GlobalParameters.packet_num + 1):
        if i not in GlobalParameters.packet_seq_list:
            GlobalParameters.loss_packet_amount += 1

    client_mn.client_socket.close()
    client_sn.client_socket.close()
    print("leaving ....... ")
    print("Loss Packet Amount: {}".format(GlobalParameters.loss_packet_amount))