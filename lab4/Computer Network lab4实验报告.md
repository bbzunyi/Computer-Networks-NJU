# Computer Network lab4实验报告

|       姓名        |   学号    |
| :---------------: | :-------: |
|      张洋彬       | 191220169 |
|       邮箱        | 完成日期  |
| 1016466918@qq.com | 2021.5.5  |

[TOC]

## 1、实验名称

### Lab 4: Forwarding Packets

## 2、实验目的
1、实现IPv4路由器的第二三步
	
2、通过查表转发发给其他主机数据包
	
3、对未知mac地址的ip地址发送ARP请求(队列实现)

## 3、实验进行

### 3.1  Preparation

​	将lab3写的文件移植到lab4中，文件结构如下：（无报告的时候）

![截屏2021-05-05 下午2.35.05](/Users/mac/Desktop/截屏2021-05-05 下午2.35.05.png)

### 3.2  IP Forwarding Table Lookup

1、首先创建一个fowarding_table表（list结构） [[network address, subnet mask, next hop IPaddr, assigned interface]]

```python
self.forwarding_table = []
```

2、对forwarding_table进行初始化，读入forwarding_table.txt文件的内容并将路由器的所有接口的信息读入forwarding_table

```python
       for intf in self.net.interfaces():
            self.forwarding_table.append([str(intf.ipaddr),str(intf.netmask),None,intf.name])#router interface 
       fo = open("forwarding_table.txt","r+")
       lines = fo.readlines()
       for line in lines :
           self.forwarding_table.append(line.split())#list type
       fo.close()
```

3、读取IPv4包的包头，进行最长前缀匹配，并对匹配的结果进行处理，逻辑在伪代码中体现

```python
ipV4=packet.get_header(IPv4)
    if ipv4 is not None
        进行最长前缀匹配
    	  match是匹配到的结果，如果没匹配到就是None
    if match is not None：
    		判断是不是发给路由器的端口，如果是不做任何处理
    		else:
          packet的IPv4的ttl--；
          如果ttl<=0就丢弃这个包（在这一阶段）
          判断下一跳是不是终点
          如果下一跳是终点：
          	判断network address是不是在arp_table中，如果在：
            	修改包的dst的mac地址
              往终点发包
            else:
              加入等待队列中，具体实现在下一节中体现
          else:
            判断next hop IPaddr是不是在arp_table中，如果在：
            	修改包的dst的mac地址
              往next hop addr发包
            else:
              加入等待队列中，具体实现在下一节中体现
            
```



### 3.3  Forwarding the Packet and ARP

​	这一阶段就是实现等待队列，主要是发送arp请求的处理：

1、首先创建了一个queue类，内有push和发包函数

```python
class Queue(object):
    def __init__(self, net: switchyard.llnetbase.LLNetBase):
        self.net=net
        self.cache = {}#list in table : dstipaddr[datetime,interface,try number,[packets]]
    def push(self,dstipaddr,intf,packet):
   
    def send_packet(self,arp_table):
```

2、cache用于缓存发往同一个地址的包，是一个dict，key是目的IP地址，value是一个list

3、push函数的实现：

```python
if dstipaddr in self.cache:
  就往packet队列里加包，加到后面（append）
else:
  新建一个项，并发送arp request
```

4、send_packet函数的实现：

```python
for dstipaddr in list(self.cache.keys()):
  if dstipaddr in arp_table:
    将里面的包全部发送到dst，然后在cache中删除这一表项
  else:
    判断距离上一个包的时间，如果时间超过1s，并且目前不足五个arp request包，就再发送一个arp_request包
    if 已经有了五个包:
      丢掉发往这个地址的包并在cache中删除
    else:
      包的数量加一，更新时间，并发送arp_request包
```

通过测试的结果如下：

![截屏2021-05-05 下午2.28.03](/Users/mac/Desktop/截屏2021-05-05 下午2.28.03.png)

​     可见，已经通过了全部测试

在mininet中测试的结果如下：

 			router的eth1和eth2的抓包结果，测试指令是`server2 ping -c2 10.1.1.1`

![截屏2021-05-05 下午4.31.30](/Users/mac/Desktop/截屏2021-05-05 下午4.31.30.png)

 ![截屏2021-05-05 下午4.31.04](/Users/mac/Desktop/截屏2021-05-05 下午4.31.04.png)
 	由上两图可知，由server2给client发包，第一次发包router1会收到arp请求，server2收到回复后，icmp包被发送到router1，然后路由器的router2给client发出了arp请求并收到了回复，将这个包转发到client，第二次发包arp_table里已经有了这些信息，所以直接发送。

##4、实验感想

​	这一阶段的代码量较多，难度也相比之前有了很大的提升，但是在做完实验后，发现只要逻辑是清楚的，整体代码也会看着比较整洁。困扰了很久的一个bug是，在对cache里的那些目标地址进行arp请求或把包发送出去的send_packet函数，应该放在while循环的最开始，也就是包处理函数的外面，不应该放在那里面。做完实验的感受是对路由器转发的过程更加清楚了，往下一跳的目标地址发送包的过程本来有点不清楚，但是跟同学讨论后发现如果下一跳不是终点的话，下一跳的目标地址就会是一个路由器的端口地址。总的来说，这次实验虽然做得比较艰辛，但是做完后基础知识的理解更加牢靠了。