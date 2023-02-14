# -5g-implementation-

資料夾socket內部放的檔案分別是客戶端與伺服器端的程式，而實驗產生的數據利用picture.py檔案產生圖片

在實作中我們使用了五台 PC 以及一台路由器作為網路系統中的 Server、基地台以及UE，並透過開源軟體srsRAN實作出虛擬SN基地台(srsENB)及虛擬UE(srsUE)
並且架構圖如下表示

![image](https://github.com/t87476909/5g-implementation/blob/main/Simulation%20results/5g.PNG)

而最終產生結果如下表示

![image](https://github.com/t87476909/5g-implementation/blob/main/Simulation%20results/result.PNG)

我們可以看到，我們的方法 OUR+DC1rx 和 OUR 在系統吞吐量的表現遠優於 FIX，證明了動態波束調度對於系統吞吐量的提升，並證明我們方法在實際網路系統環境中的可行性和優越性，同時從 OUR+DC1rx 和 OUR 之間的系統吞吐量差距中，我們也可以看到雙連接系統對於系統吞吐量的提升。
