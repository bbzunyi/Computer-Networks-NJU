# Computer Network lab2实验报告

|       姓名        |   学号    |
| :---------------: | :-------: |
|      张洋彬       | 191220169 |
|       邮箱        | 完成日期  |
| 1016466918@qq.com | 2021.4.5  |

[TOC]

## 1、实验名称

###          Lab 2: Learning Switch 

## 2.实验目的

​	1、理解switch的各种机制

​	2、自己在minine中t对所写的交换机进行传包测试

​	3、根据流程图实现代码

## 3、实验进行

### 3.1  Preparation

​	目的：创建不同版本的myswitch.py，在这些文件中实现交换机的功能。
![截屏2021-04-05 下午5.46.06](/Users/mac/Library/Application Support/typora-user-images/截屏2021-04-05 下午5.46.06.png)     

### 3.2  Basic Switch

![截屏2021-04-05 下午1.22.03](/Users/mac/Library/Application Support/typora-user-images/截屏2021-04-05 下午1.22.03.png)

​	根据流程图可以知道，要做的第一步是记录发送方Mac地址和端口，第二步就是判断是否是发送给自己的（如果是，就什么都不做，打印消息），目标方的MAC地址是否在table的key中，如果在就直接从记录的端口发送，如果不在就往除了发送方的端口发送包。

需注意：

​	如果包的目的地址是`FF：FF：FF：FF：FF：FF`(ip地址没有对应的mac地址),此时就会广播。且`FF：FF：FF：FF：FF：FF`不会被存到学习表中。

代码实现如下:
1、创建学习表

```python
 table={}#dictionary type table
```
2、更新发送方端口

```python
table[eth.src] = fromIface #update the fromIface of Mac address
```
3、通过目标方链接端口发送包

```python
 elif eth.dst in table.keys():
      toIface = table[eth.dst]
      for intf in my_interfaces:
           if toIface == intf.name:
           log_info (f"Flooding packet {packet} to {intf.name}")
           net.send_packet(intf, packet)
```
在mininet中进行测试，流程如下：
- 启动Mininet,并`xterm switch`执行`swyard myswitch.py`

- 用`wireshark server1 &` 和`wireshark server2 &`对server1和2进行抓包

- `client ping -c 2 192.168.100.1`

抓包结果如下图所示
Server2

![截屏2021-04-02 上午11.21.07](/Users/mac/Desktop/截屏2021-04-02 上午11.21.07.png)

Server1

![截屏2021-04-02 上午11.21.59](/Users/mac/Desktop/截屏2021-04-02 上午11.21.59.png)

![截屏2021-04-02 上午11.22.13](/Users/mac/Desktop/截屏2021-04-02 上午11.22.13.png)

​    由抓包结果可见，第一次client发包由于server1并没有加入学习表中，会向server1和server2都发送包，然后server1回回应client，第二次由于server1已经加入表中，所以第二次会直接往server1发包，server2不会收到广播包。

### 3.3 Timeouts

![截屏2021-04-05 下午1.22.50](/Users/mac/Library/Application Support/typora-user-images/截屏2021-04-05 下午1.22.50.png)

​	根据流程图可知，基础情况和task1差不多，只是需要在字典中添加记录时间，并每次发包时删除超过10s的包，并将目标方的时间更新。通过相关知识的学习，需引入datetime类。

代码的具体实现如下：

1、发包前的设置与删除

```python
  now=datetime.now()#获取现在的时间
  for key in list(table.keys()):#在第四部分说明这个问题
      elapsed_time=now.timestamp() - table[key][1].timestamp()
      if elapsed_time>=10:
      del table[key]
      log_debug (f"table entry with Mac Address {key} has been removed from learning switch table ")
                
  log_debug (f"In {net.name} received packet {packet} on {fromIface}")
  eth = packet.get_header(Ethernet)
  table[eth.src] = [fromIface,datetime.now()] #update the fromIface of Mac address
```

2、通过储存的端口发包

```python
  elif eth.dst in table.keys():
       toIface = table[eth.dst][0]#这里需要注意
       for intf in my_interfaces:
           if toIface == intf.name:
           log_info (f"Flooding packet {packet} to {intf.name}")
           net.send_packet(intf, packet)
```

测试的结果如下图所示，可见已全部通过。

![截屏2021-04-05 下午2.37.03](/Users/mac/Desktop/截屏2021-04-05 下午2.37.03.png)

在mininet中进行测试，流程如下：

- 启动Mininet,并`xterm switch`执行`swyard myswitch_to.py`

- 用`wireshark server1 &` 和`wireshark server2 &`对server1和2进行抓包

- `client ping -c 2 192.168.100.1`连续传两个包，观察抓包结果

- 等待10s，再次输入`client ping -c 2 192.168.100.1`

第一次抓包结果和3.2相同，第二次抓包结果如下图所示：

Server1

![截屏2021-04-05 下午3.09.13](/Users/mac/Desktop/截屏2021-04-05 下午3.09.13.png)

Server2

![截屏2021-04-05 下午3.06.49](/Users/mac/Desktop/截屏2021-04-05 下午3.06.49.png)



​    在等待超过10s后的一次ping，client和server1都被移除，这次client会给server1和server2都发送请求包，但是server2不会收到回复包。

### 3.4  Least Recently Used

![截屏2021-04-05 下午3.19.23](/Users/mac/Library/Application Support/typora-user-images/截屏2021-04-05 下午3.19.23.png)

​	根据流程图，可以得知需要作出的改变有：

​	1、字典里的value[1]存储年龄

​	2、每次发包用一个while循环，将所有table里的key的age加1

​	3、如果在表中且端口不发生变化的话，age不做任何改变，其余情况需将age变为0

​	4、如果表满的话，删除age最大的元素

```python
        for key in table.keys():
            table[key][1] += 1 #age++
        
        if eth.src in table.keys():
            if fromIface == table[eth.src][0]
            table[eth.src][0] = fromIface  #只需更新端口
            else
            table[eth.src]=[fromIface,0]
        elif len(table) < max_rule_num:
            table[eth.src]=[fromIface,0]
        else:
            max_key=list(table.keys())[0]
            for key in table.keys():
                if table[key][1]>table[max_key][1]:
                    max_key=key
            del table[max_key] #删除age最大的元素
            table[eth.src]=[fromIface,0]
```
```python
        elif eth.dst in table.keys():
            toIface = table[eth.dst][0]
            table[eth.dst][1]=0 #将age设置成0
```
由下图可见，通过了全部测试用例：
![截屏2021-04-05 下午4.32.12](/Users/mac/Desktop/截屏2021-04-05 下午4.32.12.png)

![截屏2021-04-05 下午4.32.26](/Users/mac/Desktop/截屏2021-04-05 下午4.32.26.png)

在mininet中进行测试，流程如下：
- 将学习表的`max_rule_num`设置为2（为了测试的方便）

- 启动Mininet,并`xterm switch`执行`swyard myswitch_lru.py`

- 用`wireshark server1 &` 和`wireshark server2 &`和`wireshark client &`对server1和2以及client进行抓包

- `server1 ping -c 1 192.168.100.3`

- `server2 ping -c 1 192.168.100.3`

- `server1 ping -c 1 192.168.100.2`

抓包结果如下图所示

client

![截屏2021-04-05 下午5.16.31](/Users/mac/Desktop/截屏2021-04-05 下午5.16.31.png)

Server1

![截屏2021-04-05 下午5.19.38](/Users/mac/Desktop/截屏2021-04-05 下午5.19.38.png)

Server2

![截屏2021-04-05 下午5.19.51](/Users/mac/Desktop/截屏2021-04-05 下午5.19.51.png)

​    在第一次通讯中，client和server1被记录在了学习表中，然后server2进入学习表中（server1被替换出去），然后会直接发包给client，然后server1进入学习表，将server2替换出去，然后再广播，找到server2并互发包。

### 3.5 Least Traffic Volume

![截屏2021-04-05 下午4.43.47](/Users/mac/Library/Application Support/typora-user-images/截屏2021-04-05 下午4.43.47.png)

根据流程图，可以得知需要作出的改变有：

​	1、字典里的value[1]存储交通数值

​	2、如果表满的话，删除traffic最小的元素

​	3、发包的目标处在表中的交通值加一

```python
        if eth.src in table.keys():
            table[eth.src][0] = fromIface
        elif len(table) < max_rule_num:
            table[eth.src]=[fromIface,0]
        else:
            min_key=list(table.keys())[0]
            for key in table.keys():
                if table[key][1]<table[min_key][1]:
                    min_key=key
            del table[min_key]#删除交通量最小的元素
            table[eth.src]=[fromIface,0]
```

```python
        elif eth.dst in table.keys():
            toIface = table[eth.dst][0]
            table[eth.dst][1] += 1
            for intf in my_interfaces:
                if toIface == intf.name:
                    log_info (f"Flooding packet {packet} to {intf.name}")
                    net.send_packet(intf, packet)
                    break
```

由下图可见，通过了全部测试用例：

![截屏2021-04-05 下午4.53.06](/Users/mac/Library/Application Support/typora-user-images/截屏2021-04-05 下午4.53.06.png)

在mininet中进行测试，流程如下：

- 将学习表的`max_rule_num`设置为2（为了测试的方便）
- 启动Mininet,并`xterm switch`执行`swyard myswitch_lru.py`
- 用`wireshark server1 &` 和`wireshark server2 &`和`wireshark client &`对server1和2以及client进行抓包
- `server1 ping -c 1 192.168.100.3`
- `server2 ping -c 1 192.168.100.3`
- `server1 ping -c 1 192.168.100.2`

client![截屏2021-04-05 下午10.53.44](/Users/mac/Desktop/截屏2021-04-05 下午10.53.44.png)

server1![截屏2021-04-05 下午10.59.07](/Users/mac/Desktop/截屏2021-04-05 下午10.59.07.png)

server2![截屏2021-04-05 下午10.56.02](/Users/mac/Desktop/截屏2021-04-05 下午10.56.02.png)

​	server1和client首先建立了连接，当server2要向client发包时，client被踢出，然后server2加入，然后就会flood，server1也会收到，然后流量更低的server2又被踢出，所以又会flood，之后的ARP包会使表中储存的是server2和client，然后server1进来会替换掉client，server2在表中，client不会收到回复的信息。

## 4、遇到的问题

1、datetime内的timestamp转换：

![截屏2021-04-05 下午11.07.20](/Users/mac/Library/Application Support/typora-user-images/截屏2021-04-05 下午11.07.20.png)
2、循环字典进行操作时出现：RuntimeError: dictionary changed size during iteration的解决方案

​	在官网看到解释：

	Dictionaries implement a tp_iter slot that returns an efficient iterator that iterates over the keys of the dictionary. During such an iteration, the dictionary should not be modified, except that setting the value for an existing key is allowed (deletions or additions are not, nor is the update() method). This means that we can write
	
	for k in dict: ...
	which is equivalent to, but much faster than
	
	for k in dict.keys(): ...
	as long as the restriction on modifications to the dictionary (either by the loop or by another thread) are not violated.
	
	意思是多字典在被循环的时候不能被循环删除和更新，除了给一个已经存在的key设置value。还说道 for kin dict: ...和for k in dict.keys(): ...效果是一样的，但是前者速度更快。

​	 那么解决方案就出来了，转换成列表形式就OK了。
>for k in list(dict.keys())

3、需注意：

​	如果包的目的地址是`FF：FF：FF：FF：FF：FF`(ip地址没有对应的mac地址),此时就会广播。且`FF：FF：FF：FF：FF：FF`不会被存到学习表中。
## 5、实验感想



​	本次实验的难度较上次有提升，但是代码量还是很少的，更重要的是整个实现过程和测试的过程，本人比较懒没有自己去写测试代码，但是争取下次可以做到实验的全部内容，感觉整个实验的设计特别有意思，是循序渐进的过程，也匿名在群里提问了，总体感觉不错。