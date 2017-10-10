#!/usr/bin/env python
#encoding: utf8
import subprocess

stdout = subprocess.check_output("getsi",shell=True)
ssid_list = [line.lstrip('ESSID:').strip('"') for line in stdout.split()]
print ssid_list
