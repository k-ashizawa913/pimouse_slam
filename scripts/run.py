#!/usr/bin/env python
#encoding: utf-8

import rospy,copy,math
from geometry_msgs.msg import Twist
from std_srvs.srv import Trigger, TriggerResponse
from pimouse_ros.msg import LightSensorValues
import time,sys

class Run():
    def __init__(self):
        self.cmd_vel = rospy.Publisher('/cmd_vel',Twist,queue_size=1)

        self.sensor_values = LightSensorValues()
        rospy.Subscriber('/lightsensors', LightSensorValues, self.callback_lightsensors)

    def callback_lightsensors(self,messages):
        self.sensor_values = messages

    def wall_front(self,ls):
        return ls.left_forward < 30 and ls.right_forward < 30

    def too_right(self,ls):
        return ls.right_side < 20

    def too_left(self,ls):
        return ls.left_side < 20

    def run(self):
        rate = rospy.Rate(10)
        data = Twist()

        data.linear.x = 0.0
        data.angular.z = 0.0
	A = time.time()
        while not rospy.is_shutdown():
	    data.linear.x = 0.0
	    data.angular.z = 0.0
            if self.wall_front(self.sensor_values):
                data.linear.x = 0.15
		#if time.time() - A < 1000:
		    #sys.exit()
            elif self.too_right(self.sensor_values):
		data.linear.x = -0.15
                data.angular.z = -2.0
            elif self.too_left(self.sensor_values):
		data.linear.x = -0.15
                data.angular.z = -3.14/4    
            else:
		data.linear.x = -0.3
                data.angular.z = -5.0
                
            self.cmd_vel.publish(data)
            rate.sleep()

if __name__ == '__main__':
    rospy.init_node('run')

    rospy.wait_for_service('/motor_on')
    rospy.wait_for_service('/motor_off')
    rospy.on_shutdown(rospy.ServiceProxy('/motor_off',Trigger).call)
    rospy.ServiceProxy('/motor_on',Trigger).call()

    w = Run()
    w.run()
