import csv
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import numpy as np
'''
data_row = [[0]elapsed_time,[1]self.throughput,[2]packet_frequency,[3]mode,[4]address,[5]ue_id] #這裡的self.throughput指的是總接收封包數量 --> 後面才會換成Mbps
一個封包大小為 1000bytes
'''
test_round = 1
#折線圖
# 指定使用字型和大小
#myfont = FontProperties(fname='D:/Programs/Lib/site-packages/matplotlib/mpl-data/fonts/ttf/msjh.ttc', size=40)
system_throughput = dict()

for i in range(3):
  system_throughput[i] = dict()

packet_frequency = list() # mode:[packet_frequency] 
#方法的話 1RX = 0 softmax = 1 static = 2
# 開啟 CSV 檔案
path  = "throughput.csv"
with open(path, newline='') as csvfile:
  # 讀取 CSV 檔案內容
  rows = csv.reader(csvfile)
  # 以迴圈輸出每一列
  for row in rows:
    float_row = [item for item in row]
    if float_row[2] not in packet_frequency:
      packet_frequency.append(float_row[2])
    if float_row[3] == "0":
      if float_row[2] not in system_throughput[0]:
        system_throughput[0][float_row[2]] = float_row[1]
      else:
        system_throughput[0][float_row[2]] += float_row[1]

    elif float_row[3] == "1":
      if float_row[2] not in system_throughput[1]:
        system_throughput[1][float_row[2]] = float_row[1]
      else:
        system_throughput[1][float_row[2]] += float_row[1]
    elif float_row[3] == "2":
      if float_row[2] not in system_throughput[2]:
        system_throughput[2][float_row[2]] = float_row[1]
      else:
        system_throughput[2][float_row[2]] += float_row[1]

system_throughput_list = dict()
for y in range(3):
  system_throughput_list[y] = list()
#print("system_throughput = ",system_throughput)
#packet_frequency = sorted(packet_frequency)
#print("packet_frequency = ",packet_frequency)
for i in range(3): #取平均值
  for j in range(len(packet_frequency)):
    #封包數 * 1000(總bytes) / 測試幾次 / bytes轉換mbps * 200ms換成秒數(1sec) = 吞吐量(Mbps)
    system_throughput_list[i].append(int(system_throughput[i][packet_frequency[j]]) * 1000 / test_round / 125000 / 200)

plt.figure()
plt.plot(packet_frequency,system_throughput_list[0],'s-',color = 'r', label="OUR+${DC_{1rx}}$")
plt.plot(packet_frequency,system_throughput_list[1],'o-',color = 'g', label="OUR")
plt.plot(packet_frequency,system_throughput_list[2],'h-',color = 'b', label="FIX")
plt.xlabel("packet_frequency")
plt.ylabel("System throughput(Mbps)")
plt.legend(loc = "best")
plt.savefig('Implementation_system_throughput.pdf')

plt.show()
#再加一張圖 plt.figure

    