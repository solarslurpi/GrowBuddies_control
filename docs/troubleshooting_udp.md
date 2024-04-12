# Wireshark Trace
Notice the filter (`udp and ip.src ==`).  This narrows packet viewing to just the udp packets.
![Wireshark Windows upd trace|400](images/wireshark_windows_udp.jpg)
# UDP Testing Using Windows 10 cmd Terminal

## Debug Firewall
`netsh firewall show state`
```bash
Firewall status:
-------------------------------------------------------------------
Profile                           = Standard
Operational mode                  = Disable
Exception mode                    = Enable
Multicast/broadcast response mode = Enable
Notification mode                 = Enable
Group policy version              = Windows Defender Firewall
Remote admin mode                 = Disable

Ports currently open on all network interfaces:
Port   Protocol  Version  Program
-------------------------------------------------------------------
8095   UDP       Any      (null)
```

## Debug if UDP Port is Being Used

 `netstat -aon | findstr :8095` - displays all network connections and listening ports that involve port 8095 on your Windows system, including the associated process IDs.

 ```bash
 netstat -aon | findstr :8095
  UDP    0.0.0.0:8095           *:*                                    4632
  UDP    0.0.0.0:8095           *:*                                    13140
  ```

`tasklist /fi "pid eq 5144"` - What is the task name of the task with process ID of 5144.
```
Image Name                     PID Session Name        Session#    Mem Usage
========================= ======== ================ =========== ============
spoolsv.exe                   5144 Services                   0     25,920 K
```

`taskkill /PID 5144 /F` - Kill process with process ID 5144

# UDP on Rasp Pi/Bash

## List Ports Used by the Processes
`$ sudo lsof -i :8095` - list the PIDs of the processes using port 8095.

```
COMMAND   PID     USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
python   3654       pi    3u  IPv4  26489      0t0  UDP *:8095
telegraf 3768 telegraf    7u  IPv4  29700      0t0  UDP localhost:34202->localhost:8095
python   4071       pi    3u  IPv4  28413      0t0  UDP *:8095
```
## Kill a process

## View Active Connections
`$sudo netstat -tunlp` - view active connections.
```
Active Internet connections (only servers)
Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name
tcp        0      0 127.0.0.1:39249         0.0.0.0:*               LISTEN      1061/node
tcp        0      0 0.0.0.0:1883            0.0.0.0:*               LISTEN      695/mosquitto
tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN      705/sshd: /usr/sbin
tcp        0      0 127.0.0.1:36413         0.0.0.0:*               LISTEN      966/code-e170252f76
tcp6       0      0 :::1883                 :::*                    LISTEN      695/mosquitto
tcp6       0      0 :::8086                 :::*                    LISTEN      750/influxd
tcp6       0      0 :::22                   :::*                    LISTEN      705/sshd: /usr/sbin
tcp6       0      0 :::9000                 :::*                    LISTEN      695/mosquitto
tcp6       0      0 :::3000                 :::*                    LISTEN      843/grafana
udp        0      0 0.0.0.0:5353            0.0.0.0:*                           479/avahi-daemon: r
udp        0      0 0.0.0.0:38602           0.0.0.0:*                           479/avahi-daemon: r
udp        0      0 127.0.0.1:8095          0.0.0.0:*                           1681/python
udp6       0      0 :::5353                 :::*                                479/avahi-daemon: r
udp6       0      0 :::53561                :::*                                479/avahi-daemon: r
```
notice the port 8095 is being used by the Python process with PID 1681.
## Find Out What App is Using the Port
`$ ps -p 1681 -f` - view the full command line of the process with PID 1681.
```
UID          PID    PPID  C STIME TTY          TIME CMD
root        1681       1  0 12:02 ?        00:00:00 /home/pi/GrowBuddies/.venv/bin/python /home/pi/GrowBuddies/growbuddiesproject/growbuddies/manage_environment.py
```