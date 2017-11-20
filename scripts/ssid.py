#!/usr/bin/env python
#encoding: utf8
import subprocess as spc

res=spc.check_output("sudo iwlist wlan0 scan | grep -e ESSID -e Quality")
lis=res.split()
ss=lis.index('ESSID:"322_hayakawalab_g"')
ss=ss-2
ra=lis[ss].split("=")
RSSI=abs(int(ra[1]))
print RSSI
