#!/usr/bin/python3
import subprocess

stdout = subprocess.check_output("iwlist wlan0 scan | grep 'ESSID:\".\+\"',shell=True")
ssid_list = [line.lstrip('ESSID:').strip('"') for line in stdout.split()]
