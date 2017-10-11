#!/usr/bin/env python
#encoding: utf8

import subprocess

cmd = "sudo iwlist wlan0 scan | grep -e ESSID -e Quality"
stdout = subprocess.check_output(cmd,shell=True)
print stdout

