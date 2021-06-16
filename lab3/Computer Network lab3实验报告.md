# Computer Network lab3实验报告

|       姓名        |   学号    |
| :---------------: | :-------: |
|      张洋彬       | 191220169 |
|       邮箱        | 完成日期  |
| 1016466918@qq.com | 2021.4.18 |

[TOC]

## 1、实验名称

### 	Lab 3: Respond to ARP

## 2.实验目的
​	1、实现IPv4路由器的第一步

​	2、对ARP请求进行回复

​	3、模拟实现ARP缓存表

## 3、实验进行

### 3.1  Preparation

​	清楚整个实验的结构：![截屏2021-04-18 下午11.23.11](/Users/mac/Library/Application Support/typora-user-images/截屏2021-04-18 下午11.23.11.png)

### 3.2  Handle ARP Requests
1、利用arp中的get_header()函数获取包的包头
```python
 arp=packet.get_header(Arp)
```
2、判断是不是arp包，如果不是就不处理，如果是就在端口中找ip地址对应的端口
```python
        if not arp is None:
            if arp.operation == 1:
                targetprotoaddr = arp.targetprotoaddr
                target = None                  
                for intf in interfaces:
                    if intf.ipaddr == targetprotoaddr:#根据ip地址找到mac地址
                        target = intf
                        break
```
3、如果找到了，就用target端口的ip和MAC地址以及发送方的ip和MAC地址创建一个ARP reply包，并发送给发送方的端口
```python
                if not target is None:
    					            arp_reply=create_ip_arp_reply(target.ethaddr,arp.senderhwaddr,target.ipaddr,arp.senderprotoaddr)
                    for intf in interfaces:
                        if intf.name == ifaceName:
                            self.net.send_packet(intf,arp_reply)
                            break
```
​	用提供的`myrouter1_testscenario.srpy`进行测试，通过了全部测试
![截屏2021-04-18 下午4.40.07](/Users/mac/Desktop/截屏2021-04-18 下午4.40.07.png)

  用以下指令，在mininet中进行测试：
- `sudo python start_mininet.py`

- `xterm router`  `swyard myrouter.py`

- `server2 wireshark -k &`

- `server2 ping -c3 192.168.200.2`

  server2的抓包结果如下：
  
  ![截屏2021-04-18 下午4.59.46](/Users/mac/Desktop/截屏2021-04-18 下午4.59.46.png)

![截屏2021-04-18 下午5.00.07](/Users/mac/Desktop/截屏2021-04-18 下午5.00.07.png)

![截屏2021-04-18 下午5.00.24](/Users/mac/Desktop/截屏2021-04-18 下午5.00.24.png)

​	第一个包是ARP request包，目标方的MAC地址并不知道（`FF：FF：FF：FF：FF：FF`），所以就会访问所有端口，找到ip地址对应的MAC地址，确定MAC地址后，即路由器收到ARP request包后，会回复一个ARP reply 包，发送方MAC地址对应之前接收方的ip地址，接收方对应之前的发送方。之后server2会向路由器发送ICMP包，本实验阶段路由器不能进行回复。

### 3.3  Cached ARP Table

1、创建一个`arp_table`用于存储arp包提供的信息

```python
self.arp_table={}#key是ip地址，value[0]是对应的MAC地址，value[1]是datetime.now()存储的时间
```

2、利用lab2中timeout机制（超过10s就清除）对`arp_table`中的表项进行清理

```python
   		  now=datetime.now()
        for key in list(self.arp_table.keys()):
            elapsed_time=now.timestamp() - self.arp_table[key][1].timestamp()
            if elapsed_time>=10:
                del self.arp_table[key]
                log_info (f"table entry with IP Address {key} has been removed from  arp_table ")
```
3、当ARP包不是None的时候，更新`arp_table`并打印

```python
   		 self.arp_table[arp.senderprotoaddr] = [arp.senderhwaddr,datetime.now()]
       print(self.arp_table)
```
test：

​	在mininet中进行测试，每隔15s，依次由client，server1，server2向路由器发包，由下图可以发现，由于间隔超过10s，在下一个表项进入之前，`arp_table`中已经清空。

![截屏2021-04-18 下午5.58.15](/Users/mac/Desktop/截屏2021-04-18 下午5.58.15.png)


## 4、实验感想



​	因为是系列实验，第一阶段比较简单，代码量很少，但更重要的是整个实现过程和测试的过程。目前已经大概理解了如何去回复一个ARP包。在整个实验的过程中，先开始困惑于为啥我写的arp已经是ARP包的header了，arp.op打上去的时候，里面居然没有可以填充的operation，后来问了下同学，大概是API里的东西被封装起来了吧，收获还是满满的，赶紧进入下一阶段。


