#!/usr/bin/env python
#encoding: utf8
import sys, rospy, math, tf, time, subprocess
from pimouse_ros.msg import MotorFreqs
from geometry_msgs.msg import Twist, Quaternion, TransformStamped, Point
from std_srvs.srv import Trigger, TriggerResponse
from pimouse_ros.srv import TimedMotion
from nav_msgs.msg import Odometry
from visualization_msgs.msg import Marker, MarkerArray

class Motor():
    def __init__(self):
	if not self.set_power(False): sys.exit(1)

	rospy.on_shutdown(self.set_power)
	self.sub_raw = rospy.Subscriber('motor_raw', MotorFreqs, self.callback_raw_freq)
	self.sub_cmd_vel = rospy.Subscriber('cmd_vel',Twist, self.callback_cmd_vel)

	self.srv_tm = rospy.Service('timed_motion',TimedMotion,self.callback_tm)

	self.srv_on = rospy.Service('motor_on', Trigger, self.callback_on)
	self.srv_off = rospy.Service('motor_off', Trigger, self.callback_off)

	self.last_time = rospy.Time.now()
	self.using_cmd_vel = False

	self.pub_odom = rospy.Publisher('odom', Odometry, queue_size=10)
	self.pub_mark = rospy.Publisher('mark' , Marker, queue_size=10)
	self.pub_markerArray = rospy.Publisher('markerArray',MarkerArray, queue_size=10)
	self.bc_odom = tf.TransformBroadcaster()

	self.x, self.y, self.th = 0.0, 0.0, 0.0
	self.vx, self.vth = 0.0, 0.0

	self.cur_time = rospy.Time.now()
	self.last_time = self.cur_time

    def set_power(self,onoff=False):
	en = "/dev/rtmotoren0"
	try:
	    with open(en,'w') as f:
		f.write("1\n" if onoff else "0\n")
	    self.is_on = onoff
	    return True
	except:
	    rospy.logerr("cannot write to " + en)

	return False

    def set_raw_freq(self,left_hz,right_hz):
	if not self.is_on:
	    rospy.logerr("not enpowered")
	    return
	
	try:
	     with open("/dev/rtmotor_raw_l0",'w') as lf,\
		  open("/dev/rtmotor_raw_r0",'w') as rf:
		 lf.write(str(int(round(left_hz))) + "\n")
		 rf.write(str(int(round(right_hz))) + "\n")
	except:
	    rospy.logerr("cannot write to rtmotor_raw_*")

    def callback_raw_freq(self,message):
	self.set_raw_freq(message.left_hz,message.right_hz)

    def callback_cmd_vel(self,message):
	if not self.is_on:
	    return
	self.vx = message.linear.x
	self.vth = message.angular.z

	forward_hz = 80000.0*message.linear.x/(9*math.pi)
	rot_hz = 400.0*message.angular.z/math.pi
	self.set_raw_freq(forward_hz-rot_hz, forward_hz+rot_hz)
	self.using_cmd_vel = True
	self.last_time = rospy.Time.now()

    def onoff_response(self,onoff):
        d = TriggerResponse()
        d.success = self.set_power(onoff)
        d.message = "ON" if self.is_on else "OFF"
        return d

    def callback_on(self,message): return self.onoff_response(True)

    def callback_off(self,message): return self.onoff_response(False)

    def callback_tm(self,message):
	if not self.is_on:

	    rospy.logerr("not enpowered")
	    return False

	dev = "/dev/rtmotor0"
	try:
	    with open(dev,'w') as f:
		f.write("%d %d %d\n" %(message.left_hz,message.right_hz,message.duration_ms))
	except:
	    rospy.logerr("cannot write to " + dev)
	    return False

	return True

    def send_odom(self):
	self.cur_time = rospy.Time.now()

	#曖昧な修正
	dt = self.cur_time.to_sec() - self.last_time.to_sec()
	self.x += self.vx * math.cos(self.th) * dt
	self.y += self.vx * math.sin(self.th) * dt
	#self.th += self.vth * dt
	self.th += (self.vth * dt) * 0.4#

	q = tf.transformations.quaternion_from_euler(0, 0, self.th)
	self.bc_odom.sendTransform((self.x,self.y,0.0), q, self.cur_time,"base_link","odom")

	odom = Odometry()

	odom.header.stamp = self.cur_time
	odom.header.frame_id = "odom"

        odom.pose.pose.position = Point(self.x,self.y,0)
        odom.pose.pose.orientation = Quaternion(*q)

	odom.child_frame_id = "base_link"
	odom.twist.twist.linear.x = self.vx
	odom.twist.twist.linear.y = 0.0
	odom.twist.twist.angular.z = self.vth

	self.pub_odom.publish(odom)
	
	self.last_time = self.cur_time

    def send_mark(self):
        self.cur_time = rospy.Time.now()
	#前回の処理から何秒経ったのか	
        dt = self.cur_time.to_sec() - self.last_time.to_sec()
        self.x += self.vx * math.cos(self.th) * dt
        self.y += self.vx * math.sin(self.th) * dt
        self.th += (self.vth * dt) * 0.4#
        q = tf.transformations.quaternion_from_euler(0, 0, self.th)

	####電波強度取得
	#cmd = 'sudo iwlist wlan0 scan | egrep -B 2 322_hayakawalab_g'
	cmd = 'sudo iwlist wlan0 scan | egrep -B 2 '+ ssid
	#指定したSSIDがある行の上２行を表示
	stdout = subprocess.check_output(cmd,shell=True)
	#print stdout
	#print stdout[28:30]
	st = float(stdout[28:30])/100.0
	#print st

	mark = Marker()
	
        mark.header.stamp = self.cur_time
	mark.header.frame_id = "odom"
	    
	id = 0
	    
	mark.ns = "marker"
	mark.id = id
	mark.type = Marker.SPHERE
	mark.action = Marker.ADD

        mark.pose.position = Point(self.x-0.2,self.y-0.2,0.2)#
        mark.pose.orientation = Quaternion(*q)

        mark.scale.x = st	#0.5
        mark.scale.y = st	#0.5
        mark.scale.z = 0.01

        mark.color.r = 0.1
        mark.color.g = 0.1
        mark.color.b = 1.0
        mark.color.a = 0.5

	count = 0

        if(count > MARKERS_MAX):
            markerArray.markers.pop(0)

        markerArray.markers.append(mark)

        id = 0
        for m in markerArray.markers:
            m.id = id
            id += 1

        self.pub_markerArray.publish(markerArray)
        count += 1

	self.last_time = self.cur_time

    def send_ssid(self):
        self.cur_time = rospy.Time.now()
        
        mark2 = Marker()

        mark2.header.stamp = self.cur_time
        mark2.header.frame_id = "odom"

        id = 0

        mark2.ns = "marker"
        mark2.id = id
        mark2.type = Marker.TEXT_VIEW_FACING
        mark2.action = Marker.ADD

	mark2.pose.position.x = -2.0
	mark2.pose.position.y = -3.0
	mark2.pose.position.z = 2.0
	mark2.pose.orientation.x = 1.0
	mark2.pose.orientation.y = 1.0
	mark2.pose.orientation.z = 1.0
	mark2.pose.orientation.w = 1.0

	mark2.text = ssid

        mark2.scale.x = 0.5
        mark2.scale.y = 0.5
        mark2.scale.z = 0.5

        mark2.color.r = 0.1
        mark2.color.g = 0.1
        mark2.color.b = 1.0
        mark2.color.a = 1.0

        self.pub_mark.publish(mark2)
        self.last_time = self.cur_time

#########ここから下試験#######

    def send_mark2(self):
        self.cur_time = rospy.Time.now()
        #前回の処理から何秒経ったのか
        dt = self.cur_time.to_sec() - self.last_time.to_sec()
        self.x += self.vx * math.cos(self.th) * dt
        self.y += self.vx * math.sin(self.th) * dt
        self.th += (self.vth * dt) * 0.4#
        q = tf.transformations.quaternion_from_euler(0, 0, self.th)

        ####電波強度取得
        cmd = 'sudo iwlist wlan0 scan | egrep -B 2 MIZUNO'
        #指定したSSIDがある行の上２行を表示
        stdout = subprocess.check_output(cmd,shell=True)
        #print stdout
        #print stdout[28:30]
        st = float(stdout[28:30])/100.0
        #print st

        mark = Marker()

        mark.header.stamp = self.cur_time
        mark.header.frame_id = "odom"

        id = 0

        mark.ns = "marker2"
        mark.id = id
        mark.type = Marker.SPHERE
        mark.action = Marker.ADD

        mark.pose.position = Point(self.x-0.2,self.y+0.2,0.4)#
        mark.pose.orientation = Quaternion(*q)

        mark.scale.x = st     
        mark.scale.y = st
        mark.scale.z = 0.01

        mark.color.r = 1.0
        mark.color.g = 0.1
        mark.color.b = 0.1
        mark.color.a = 0.5

        count = 0

        if(count > MARKERS_MAX):
            markerArray.markers.pop(0)

        markerArray.markers.append(mark)

        id = 0
        for m in markerArray.markers:
            m.id = id
            id += 1

        self.pub_markerArray.publish(markerArray)
        count += 1

        self.last_time = self.cur_time

    def send_ssid2(self):
        self.cur_time = rospy.Time.now()

        mark2 = Marker()

        mark2.header.stamp = self.cur_time
        mark2.header.frame_id = "odom"

        id = 0

        mark2.ns = "marker2"
        mark2.id = id
        mark2.type = Marker.TEXT_VIEW_FACING
        mark2.action = Marker.ADD

        mark2.pose.position.x = -1.0
        mark2.pose.position.y = -3.0
        mark2.pose.position.z = 2.0
        mark2.pose.orientation.x = 1.0
        mark2.pose.orientation.y = 1.0
        mark2.pose.orientation.z = 1.0
        mark2.pose.orientation.w = 1.0

        mark2.text = ssid2

        mark2.scale.x = 0.5
        mark2.scale.y = 0.5
        mark2.scale.z = 0.5

        mark2.color.r = 1.0
        mark2.color.g = 0.1
        mark2.color.b = 0.1
        mark2.color.a = 1.0

        self.pub_mark.publish(mark2)
        self.last_time = self.cur_time


    def send_mark3(self):
        self.cur_time = rospy.Time.now()
        #前回の処理から何秒経ったのか
        dt = self.cur_time.to_sec() - self.last_time.to_sec()
        self.x += self.vx * math.cos(self.th) * dt
        self.y += self.vx * math.sin(self.th) * dt
        self.th += (self.vth * dt) * 0.4#
        q = tf.transformations.quaternion_from_euler(0, 0, self.th)

        ####電波強度取得
        #cmd = 'sudo iwlist wlan0 scan | egrep -B 2 322_hayakawalab_g'
        cmd = 'sudo iwlist wlan0 scan | egrep -B 2 '+ ssid3
        #指定したSSIDがある行の上２行を表示
        stdout = subprocess.check_output(cmd,shell=True)
        #print stdout
        #print stdout[28:30]
        st = float(stdout[28:30])/100.0
        #print st

        mark = Marker()

        mark.header.stamp = self.cur_time
        mark.header.frame_id = "odom"

        id = 0

        mark.ns = "marker3"
        mark.id = id
        mark.type = Marker.SPHERE
        mark.action = Marker.ADD

        mark.pose.position = Point(self.x+0.2,self.y+0.2,0.6)
        mark.pose.orientation = Quaternion(*q)

        mark.scale.x = st       #0.5
        mark.scale.y = st       #0.5
        mark.scale.z = 0.01

        mark.color.r = 0.1
        mark.color.g = 1.0
        mark.color.b = 0.1
        mark.color.a = 0.5

        count = 0

        if(count > MARKERS_MAX):
            markerArray.markers.pop(0)

        markerArray.markers.append(mark)

        id = 0
        for m in markerArray.markers:
            m.id = id
            id += 1

        self.pub_markerArray.publish(markerArray)
        count += 1

        self.last_time = self.cur_time

    def send_ssid3(self):
        self.cur_time = rospy.Time.now()

        mark2 = Marker()

        mark2.header.stamp = self.cur_time
        mark2.header.frame_id = "odom"

        id = 0

        mark2.ns = "marker3"
        mark2.id = id
        mark2.type = Marker.TEXT_VIEW_FACING
        mark2.action = Marker.ADD

        mark2.pose.position.x = -0.0
        mark2.pose.position.y = -3.0
        mark2.pose.position.z = 2.0
        mark2.pose.orientation.x = 1.0
        mark2.pose.orientation.y = 1.0
        mark2.pose.orientation.z = 1.0
        mark2.pose.orientation.w = 1.0

        mark2.text = ssid3

        mark2.scale.x = 0.5
        mark2.scale.y = 0.5
        mark2.scale.z = 0.5

        mark2.color.r = 0.1
        mark2.color.g = 1.0
        mark2.color.b = 0.1
        mark2.color.a = 1.0

        self.pub_mark.publish(mark2)
        self.last_time = self.cur_time


    def send_mark4(self):
        self.cur_time = rospy.Time.now()
        #前回の処理から何秒経ったのか
        dt = self.cur_time.to_sec() - self.last_time.to_sec()
        self.x += self.vx * math.cos(self.th) * dt
        self.y += self.vx * math.sin(self.th) * dt
        self.th += (self.vth * dt) * 0.4#
        q = tf.transformations.quaternion_from_euler(0, 0, self.th)

        ####電波強度取得
        #cmd = 'sudo iwlist wlan0 scan | egrep -B 2 322_hayakawalab_g'
        cmd = 'sudo iwlist wlan0 scan | egrep -B 2 '+ ssid4
        #指定したSSIDがある行の上２行を表示
        stdout = subprocess.check_output(cmd,shell=True)
        #print stdout
        #print stdout[28:30]
        st = float(stdout[28:30])/100.0
        #print st

        mark = Marker()

        mark.header.stamp = self.cur_time
        mark.header.frame_id = "odom"

        id = 0

        mark.ns = "marker4"
        mark.id = id
        mark.type = Marker.SPHERE
        mark.action = Marker.ADD

        mark.pose.position = Point(self.x+0.2,self.y-0.2,0.8)
        mark.pose.orientation = Quaternion(*q)

        mark.scale.x = st       #0.5
        mark.scale.y = st       #0.5
        mark.scale.z = 0.01

        mark.color.r = 0.5
        mark.color.g = 0.1
        mark.color.b = 0.5
        mark.color.a = 0.5

        count = 0

        if(count > MARKERS_MAX):
            markerArray.markers.pop(0)

        markerArray.markers.append(mark)

        id = 0
        for m in markerArray.markers:
            m.id = id
            id += 1

        self.pub_markerArray.publish(markerArray)
        count += 1

        self.last_time = self.cur_time

    def send_ssid4(self):
        self.cur_time = rospy.Time.now()

        mark2 = Marker()

        mark2.header.stamp = self.cur_time
        mark2.header.frame_id = "odom"

        id = 0

        mark2.ns = "marker4"
        mark2.id = id
        mark2.type = Marker.TEXT_VIEW_FACING
        mark2.action = Marker.ADD

        mark2.pose.position.x = +1.0
        mark2.pose.position.y = -3.0
        mark2.pose.position.z = 2.0
        mark2.pose.orientation.x = 1.0
        mark2.pose.orientation.y = 1.0
        mark2.pose.orientation.z = 1.0
        mark2.pose.orientation.w = 1.0

        mark2.text = ssid4

        mark2.scale.x = 0.5
        mark2.scale.y = 0.5
        mark2.scale.z = 0.5

        mark2.color.r = 0.5
        mark2.color.g = 0.1
        mark2.color.b = 0.5
        mark2.color.a = 1.0

        self.pub_mark.publish(mark2)
        self.last_time = self.cur_time


	
if __name__ == '__main__':
    rospy.init_node('motors')
    m = Motor()
    rate = rospy.Rate(10)
    t = time.time()
    MARKERS_MAX = 100
    markerArray = MarkerArray()
    ssid = '322_hayakawalab_g'
    ssid2 = 'MIZUNO WORKTIME'
    ssid3 = '001D73A9FA20_G'
    ssid4 = '438Ogawa-g'
    while not rospy.is_shutdown():
	m.send_odom()
	m.send_ssid()
	m.send_ssid2()
	m.send_ssid3()
	m.send_ssid4()
	rate.sleep()
	if ( time.time() - t )  >  10 :
	    t = time.time() 
	    m.send_mark()
	    m.send_mark2()
	    m.send_mark3()
	    m.send_mark4()
	    rate.sleep()
