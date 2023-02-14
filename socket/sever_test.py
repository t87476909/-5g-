from logging import error
from threading import Thread
from sklearn import preprocessing
import numpy as np
import math
import cmath
import socket
import time
import random
import csv
#我有更改過buffer
host = "0.0.0.0"
port = 20001
sn_ip = "192.168.0.153" #自己本身ip 192.168.1.3
mode = "static" #1RX softmax static

simualtion_time = 100 #sec
#packet_num = 100000
beam_number = 4
packet_frequency = 1200 #200 400 600 800 1000 (1200 1600 2000 2400 2800 3200)
bs_beam_relation = {"mn":{"sn":{2:4}}} #mn基地台與sn基地台


class SocketServer(Thread):
    def __init__(self, host, port):
        super().__init__()
        #self.seq_count = {}
        #self.timer = {}
        self.throughput = 0
        #self.ue_throughput = {}
        self.csv_write = True
        self.flag = False
        self.split_ratio = 5
        self.buffer = {}
        self.address_dict = {} # Format -> {"1": {"mn": ("192.168.1.3", 50001), "sn": ("192.168.1.2", 50002)}, "2": {"mn": ("192.168.1.4", 50003), "sn": ("192.168.1.2", 50004)}, ...]
        self.beam_ue_table = {} # Format -> [bs_address]:{beam:ue_id}
        self.bs_transmit_ue_time = {} # [bs_address]:{ue_id:time_list}
        self.bs_transmit_throughput = {}
        self.one_rx_before_beam_list = {}
        self.weights = {}
        self.start_time = round(time.time()) #轉換為ms單位

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)

    def run(self):
        while True:
            connection, address = self.server_socket.accept() # 等待Client連線
            ue_id = connection.recv(1024).decode("utf-8") # 接收UE ID
            print("UE ID: {}, Address: {} is connected".format(ue_id, address))
            
            #self.timer.setdefault(ue_id, [0, 0]) # 初始化timer的UE ID為[0, 0]
            #self.seq_count.setdefault(ue_id, 0) # 初始化seq_count的UE ID為0

            self.buffer.setdefault(address, {}) # 初始化連線Address的Buffer
            self.buffer[address].setdefault(ue_id, []) # 初始化連線Address的Buffer

            self.address_dict.setdefault(ue_id, {}) # 建立UE的Address Dictionary

            self.bs_transmit_ue_time.setdefault(address, {}) # 建立bs連接ue的時間
            self.bs_transmit_ue_time[address].setdefault(ue_id,[])

            self.bs_transmit_throughput.setdefault(address,{})
            self.bs_transmit_throughput[address].setdefault(ue_id,0)

            self.one_rx_before_beam_list[address] = list()
            self.beam_ue_table.setdefault(address, {}) # 建立bs波束底下的ue

            for beam in range(beam_number):
                self.beam_ue_table[address].setdefault(beam, [])

            if self.address_dict[ue_id] == {}:
                self.new_traffic_controller(ue_id=ue_id) # 建立UE的Traffic產生器，將封包加到Buffer
            if address[0] == sn_ip:
                self.address_dict[ue_id]["sn"] = address # 將SN Address加入Address Dictionary
            else:
                self.address_dict[ue_id]["mn"] = address # 將MN Address加入Address Dictionary
            self.time_generator(address,ue_id) #生成最初始的靜態波束
            self.bs_time_update(address=address)
            self.new_connection(connection=connection, ue_id=ue_id, address=address) # 開新的Thread送Buffer的資料到Client

    def new_traffic_controller(self, ue_id):
        Thread(target=self.traffic_controller,
               kwargs={"ue_id": ue_id},
               daemon=True).start()

    def traffic_controller(self, ue_id):
        sequence = 0
        data = "0" * 980
        keep_going = True
        while(keep_going):
            elapsed_time = round(time.time()) - self.start_time
            #if "mn" in self.address_dict[ue_id]:
            if self.flag == True:
                for _ in range(packet_frequency):
                    sequence += 1
                    packet_str = "seq:{},data:{}".format(str(sequence).zfill(10), data)
                    packet = bytes(packet_str, encoding = "utf-8")

                    if "sn" in self.address_dict[ue_id] and "mn" in self.address_dict[ue_id]:
                        target_bs = random.choices(list(self.address_dict[ue_id].keys()), weights=((10 - self.split_ratio), self.split_ratio))[0]
                        target_address = self.address_dict[ue_id][target_bs]
                        self.buffer[target_address][ue_id].append(packet)
                    elif "sn" in self.address_dict[ue_id]:
                        self.buffer[self.address_dict[ue_id]["sn"]][ue_id].append(packet)
                    else:
                        self.buffer[self.address_dict[ue_id]["mn"]][ue_id].append(packet)
                    '''
                    if "sn" in self.address_dict[ue_id]:
                        target_bs = random.choices(list(self.address_dict[ue_id].keys()), weights=((10 - self.split_ratio), self.split_ratio))[0]
                        target_address = self.address_dict[ue_id][target_bs]
                        self.buffer[target_address][ue_id].append(packet)
                    else:
                        self.buffer[self.address_dict[ue_id]["mn"]][ue_id].append(packet)
                    '''
                    if elapsed_time >= simualtion_time:
                        keep_going = False
                        
                        #if sequence >= packet_num:
                        #    keep_going = False

                time.sleep(0.1) #每0.1秒1000個封包
            
            else:
                time.sleep(0.1)

    def new_connection(self, connection, ue_id, address):
        Thread(target=self.send_data_to_client,
               kwargs={"connection": connection, "ue_id": ue_id, "address": address},
               daemon=True).start()

    def send_data_to_client(self, connection, ue_id, address):
        keep_going = True
        while keep_going:
            #if self.seq_count[ue_id] >= packet_num:
            #    keep_going = False
            elapsed_time = round(time.time()) - self.start_time
            if elapsed_time >= simualtion_time:
                keep_going = False
            #print("elapsed_time = ",elapsed_time)
            #print("bs = {} ue_id = {} time = {} current_time = {}".format(address,ue_id,self.bs_transmit_ue_time[address][ue_id],round(time.time())))
            if len(self.bs_transmit_ue_time[address][ue_id]) > 0:
                if self.bs_transmit_ue_time[address][ue_id][0] == round(time.time()):
                    #print("--------------------- send data -------------------")
                    #print("address = ",address)
                    if len(self.buffer[address][ue_id]) > 0:
                        send_data = self.buffer[address][ue_id][0]
                        #print("send_data = ",send_data)
                        try:
                            connection.send(send_data)
                            self.bs_transmit_throughput[address][ue_id] += 1
                            #self.ue_throughput[ue_id] += 1
                            self.throughput += 1
                            del self.buffer[address][ue_id][0]

                        except:
                            print("Send Packet Error")
                            keep_going = False
                    #else:
                    #    time.sleep(0.1)
                            
                elif self.bs_transmit_ue_time[address][ue_id][0] < round(time.time()): #處理例外狀況(bs連接ue時間追不上)
                    #print("delete_time = ",self.bs_transmit_ue_time[address][ue_id][0])
                    del self.bs_transmit_ue_time[address][ue_id][0]
        
        connection.close()

        print("close connection {}".format(address))
        print("elapsed_time = ",elapsed_time)
        print("self.throughput = ",self.throughput)
        path = "throughput.csv"
        with open(path, 'a+', newline='') as f:
            csv_write = csv.writer(f)
            data_row = [elapsed_time,self.throughput,packet_frequency,mode,address,ue_id]
            csv_write.writerow(data_row)
            #print(self.timer[ue_id][1] - self.timer[ue_id][0])
    
    def bs_time_update(self,address):
        Thread(target= self.time_update,
            kwargs={"address": address},
            daemon=True).start()

    def time_update(self,address): #每隔4ms(波束數量)要更改一次就可以
        keep_going = True
        beam_list = [i for i in range(beam_number)] #bs的波束表
        while keep_going:
            if self.flag == True:
                elapsed_time = round(time.time()) - self.start_time #經過時間(ms)
                if elapsed_time >= simualtion_time:
                    keep_going = False
                if (elapsed_time % 4) == 0: #每過4ms更新一次時間
                    time.sleep(0.98) #要讓send_data盡量多送一點
                    if mode == 'static':
                        for i in range(beam_number):
                            ue_id_list = self.beam_ue_table[address][beam_list[i]] #要更改時間的ue_id列表
                            if len(ue_id_list) != 0:
                                for j in range(len(ue_id_list)):
                                    self.bs_transmit_ue_time[address][ue_id_list[j]].append(round(time.time()) + i + 4)
                        
                        for adr,ue in self.bs_transmit_ue_time.items():
                            if address != adr:
                                for ue_id,open_time in ue.items():
                                    if ue_id in self.bs_transmit_ue_time[address]:
                                        #print("-----------------------------------------------------------------------------------------")
                                        #print("address = {} adr = {} 修改後最新的self.bs_transmit_ue_time[address][ue_id] = {} self.bs_transmit_ue_time[adr][ue_id] = {}".format(address,adr,self.bs_transmit_ue_time[address][ue_id],self.bs_transmit_ue_time[adr][ue_id]))
                                        new_time_list = list(set(self.bs_transmit_ue_time[address][ue_id]) - set(self.bs_transmit_ue_time[adr][ue_id]))
                                        new_time_list.sort()
                                        self.bs_transmit_ue_time[address][ue_id] = new_time_list
                                        #print("address = {} 修改後最新的self.bs_transmit_ue_time[address][ue_id] = {}".format(address,self.bs_transmit_ue_time[address][ue_id]))
                        
                    elif mode == '1RX' or mode == 'softmax':
                        remain_data_list = list() #基地台波束剩餘流量
                        transmit_data_list = list() #基地台波束傳輸流量
                        current_beam_list = list() #當前生成的波束
                        for i in range(beam_number):
                            data_size = 0
                            transmit_data_size = 0
                            ue_id_list = self.beam_ue_table[address][beam_list[i]] #遍立所有的ue_id列表
                            if len(ue_id_list) != 0: #該波束底下有ue_id
                                for j in range(len(ue_id_list)):
                                    transmit_data_size = self.bs_transmit_throughput[address][ue_id_list[j]]
                                    data_size = data_size + len(self.buffer[address][ue_id_list[j]])
                            remain_data_list.append(data_size) #統計波束剩餘流量 format[0 1 2 3]
                            self.weights[address] = sum(remain_data_list) #紀錄基地台權重
                            transmit_data_list.append(transmit_data_size)
                        #print("transmit_data_list = {} remain_data_list = {}".format(transmit_data_list,remain_data_list))
                        probability = self.get_probability(transmit_data_list,remain_data_list) #獲取最終機率結果
                        #print("probability = ",probability)
                        for i in range(beam_number):
                            add_beam = np.random.choice(beam_list,p = probability) #若生成波束
                            ue_id_list = self.beam_ue_table[address][add_beam] #要加的ue_id生成
                            current_beam_list.append(add_beam)
                            
                        if len(self.one_rx_before_beam_list[address]) != 0: #表示已經有生成過一次波束了
                            minus = list(set(beam_list)-set(self.one_rx_before_beam_list[address])) #必定生成波束(差集)
                            exchange_beam_list = current_beam_list[:] #記錄除必定生成波束外剩下需要放入的波束
                            final_beam_list = list()
                            for i in range(len(minus)):
                                if minus[i] in exchange_beam_list: #必定生成波束在排序波束中
                                    exchange_beam_list.remove(minus[i]) 
                                else: #必定生成波束不再生成波束中 刪除最小的波束
                                    min_data_size = min(remain_data_list)                               
                                    index = remain_data_list.index(min_data_size)
                                    del remain_data_list[index]
                                    del exchange_beam_list[index]

                            exchange_index_list = list()
                            exchange_or_not_list = list()
                            #print("current_beam_list = {} minus = {} ".format(current_beam_list,minus))
                            for i in range(beam_number): #生成波束交換波束結果
                                if i < len(minus):
                                    current_beam_list[i] = minus[i]
                                else:
                                    exchange_index_list.append(i)
                                    exchange_or_not_list.append(-1) #-1代表該位置的波束可以更動
                                    current_beam_list[i] = exchange_beam_list.pop(0)

                            if mode == '1RX':
                                max_bs_address = max(self.weights, key=self.weights.get)
                                if address != max_bs_address: #假設該基地台不是最大基地台權重的話 他要被修改
                                    if len(exchange_index_list) > 1:
                                        for i in range(len(exchange_index_list)):
                                            index = exchange_index_list[i] #可交換的原先波束時槽
                                            if current_beam_list[index] == 2 and self.one_rx_before_beam_list[max_bs_address][index] == 4: #波束如果是2或4的話那就有波束相交的機會
                                                for j in range(len(exchange_or_not_list)):
                                                    exchange_index = exchange_index_list[j]
                                                    if exchange_index != index and current_beam_list[exchange_index] != 2: #判斷當前交換波束時槽是否不一樣
                                                        if exchange_or_not_list[i] == -1 and exchange_or_not_list[j] == -1: #判斷當前交換波束時槽是否可以交換
                                                            current_beam_list[index],current_beam_list[exchange_index] =  current_beam_list[exchange_index],current_beam_list[index]
                                                            exchange_or_not_list[i] == 1
                                                            break
                                            elif current_beam_list[index] == 4 and self.one_rx_before_beam_list[max_bs_address][index] == 2:
                                                for j in range(len(exchange_or_not_list)):
                                                    exchange_index = exchange_index_list[j]
                                                    if exchange_index != index and current_beam_list[exchange_index] != 2:
                                                        if exchange_or_not_list[i] == -1 and exchange_or_not_list[j] == -1:
                                                            current_beam_list[index],current_beam_list[exchange_index] =  current_beam_list[exchange_index],current_beam_list[index]
                                                            exchange_or_not_list[i] == 1
                                                            break
                            '''
                            if mode == '1RX':
                                max_bs_address = max(self.weights, key=self.weights.get)
                                if len(self.weights.values()) != 0: #所有多基地台還沒分配完畢
                                    if address != max_bs_address: #假設SN基地台不是最大基地台權重的話 他要被修改
                                        if len(exchange_index_list) > 1: #剩餘的可交換波束時槽 > 1
                                            for i in range(len(exchange_index_list)):
                                                index = exchange_index_list[i] #交換的原先波束
                                                
                                                if current_beam_list[index] == 2: #波束相交的地方只有MN 4波束 與 SN2波束
                                                    for j in range(len(exchange_index_list)):
                                                        exchange_index = exchange_index_list[j] #要被交換的波束位置
                                                        if exchange_index == index:
                                                            current_beam_list[index],current_beam_list[exchange_index] =  current_beam_list[exchange_index],current_beam_list[index]
                                                            exchange_index_list.remove(index) #可交換波束時槽剃除
                                                            break
                            '''
                        for i in range(beam_number):
                            beam = current_beam_list[i]
                            ue_id_list = self.beam_ue_table[address][beam] #要加的ue_id生成
                            if len(ue_id_list) != 0:
                                for j in range(len(ue_id_list)):
                                    self.bs_transmit_ue_time[address][ue_id_list[j]].append(round(time.time()) + i + 4)
                                    #self.bs_transmit_ue_time[address][ue_id_list[j]].sort()
                        
                        if mode == 'softmax': #不同address 同 ue_id 同time 要刪除一個
                            for adr,ue in self.bs_transmit_ue_time.items():
                                if address != adr:
                                    #print("-------------------------------------------------------------")
                                    #print("self.bs_transmit_ue_time = ",self.bs_transmit_ue_time)
                                    for ue_id,open_time in ue.items():
                                        #print("ue_id = ",ue_id)
                                        #print("原self.bs_transmit_ue_time[address][ue_id] = ",self.bs_transmit_ue_time[address][ue_id])
                                        if ue_id in self.bs_transmit_ue_time[address]:
                                            new_time_list = list(set(self.bs_transmit_ue_time[address][ue_id]) - set(self.bs_transmit_ue_time[adr][ue_id]))
                                            new_time_list.sort()
                                            self.bs_transmit_ue_time[address][ue_id] = new_time_list
                                        #print("更改後self.bs_transmit_ue_time[address][ue_id] = ",self.bs_transmit_ue_time[address][ue_id])
                        
                        #print("self.bs_transmit_ue_time[address][ue_id_list[j]] = ",self.bs_transmit_ue_time[address][ue_id_list[j]])
                        #print("current_beam_list = ",current_beam_list)
                        self.one_rx_before_beam_list[address] = current_beam_list #紀錄此次基地台打出來的波束(用來生成下一次波束用的)
                    #time.sleep(0.1) #避免動作重複執行(4ms執行一次)

    def time_generator(self,address,ue_id): #要加入self.beam_ue_table
        if len(self.bs_transmit_ue_time[address][ue_id]) == 0: #判斷有沒有初始的生成時間
            if 'mn' in self.address_dict[ue_id] and 'sn' in self.address_dict[ue_id]: #有mn也有sn
                if self.address_dict[ue_id]["mn"] == address: #UE初始位置默認放在MN基地台的波束2
                    self.beam_ue_table[address][1].append(ue_id)
                    self.bs_transmit_ue_time[address][ue_id].append(self.start_time + 2) # mn + 2
                elif self.address_dict[ue_id]["sn"] == address: #UE初始位置默認放在SN基地台的波束4
                    self.beam_ue_table[address][3].append(ue_id)
                    self.bs_transmit_ue_time[address][ue_id].append(self.start_time + 4) # sn + 4

            elif 'sn' not in self.address_dict[ue_id] and 'mn' in self.address_dict[ue_id]: #只有mn #UE初始位置默認放在MN基地台的波束4
                self.beam_ue_table[address][3].append(ue_id)
                self.bs_transmit_ue_time[address][ue_id].append(self.start_time + 4)

            elif 'sn' in self.address_dict[ue_id] and 'mn' not in self.address_dict[ue_id]: #只有sn #UE初始位置默認放在SN基地台的波束3
                self.beam_ue_table[address][2].append(ue_id)
                self.bs_transmit_ue_time[address][ue_id].append(self.start_time + 4)
            #print("self.address_dict[ue_id] = ",self.address_dict[ue_id])

    def softmax(self,throughtput): #區域總流量正規化
        throughtput = throughtput - np.max(throughtput)
        exp_throughtput = np.exp(throughtput)
        softmax_throughtput = exp_throughtput / np.sum(exp_throughtput)
        return softmax_throughtput

    def get_probability(self,transmit_data_list,remain_data_list):
        
        final_probability = list()
        z_normalization_transmit_data = preprocessing.scale(transmit_data_list, axis=0, with_mean=True, with_std=True, copy=True) #傳輸流量標準化
        z_normalization_remain_data = preprocessing.scale(remain_data_list, axis=0, with_mean=True, with_std=True, copy=True) #剩餘流量標準化
        transmit_probability = self.softmax(z_normalization_transmit_data) #標準化數值換成機率
        remain_probability = self.softmax(z_normalization_remain_data) #標準化數值換成機率

        if 0 in transmit_data_list: #判斷是否有流量為0的波束
            zero_transmit_probability = 0
            for i in range(beam_number): #遍立所有波束時槽
                if transmit_data_list[i] == 0:
                    zero_transmit_probability += transmit_probability[i]
                    transmit_probability[i] = 0
            for j in range(beam_number):
                if transmit_data_list[j] != 0:
                    transmit_probability[j] = transmit_probability[i] / (1 - zero_transmit_probability)

        if 0 in remain_data_list:
            zero_remain_probability = 0
            for i in range(beam_number): #遍立所有波束時槽
                if remain_data_list[i] == 0:
                    zero_remain_probability += remain_probability[i]
                    remain_probability[i] = 0
            for j in range(beam_number):
                if remain_data_list[j] != 0:
                    remain_probability[j] = remain_probability[i] / (1 - zero_remain_probability)

        sum_all_probability = sum(transmit_probability) + sum(remain_probability)
        if sum_all_probability > 1.1:
            for i in range(beam_number):
                probability = (transmit_probability[i] + remain_probability[i]) / 2
                final_probability.append(probability)
            return final_probability
        elif sum(transmit_probability) > 0.1 and sum(remain_probability) < 0.1:
            return transmit_probability
        elif sum(transmit_probability) < 0.1 and sum(remain_probability) > 0.1:
            return remain_probability
        else:
            none_data_probability = list()
            probability_input = 1 / beam_number
            for i in range(beam_number):
                none_data_probability.append(probability_input)
            #np_probability_data = np.array(none_data_probability)
            return none_data_probability

if __name__ == '__main__':
    server = SocketServer(host, port)
    server.setDaemon(True)
    server.start()

    # because we set daemon is true, so the main thread has to keep alive
    while True:
        command = input()
        if command == "end":
            break
        elif command == "s":
            #print("stest")
            server.flag = True
            server.start_time = round(time.time())
    
    server.server_socket.close()
    print("leaving ....... ")
