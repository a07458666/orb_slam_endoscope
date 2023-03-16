import cv2
import sys
sys.path.append('/home/aaeon/workspace/orb_slam_endoscope/ORB_SLAM3/lib/')
from imaislam import Imaislam
import matplotlib.pyplot as plt 
import os
import time 
from datetime import datetime
import math
#video_path = './2022050601.mp4'
# video_path = '/home/aaeon/maskyolo/video/2022021501.mp4'
# vidcap = cv2.VideoCapture(video_path)
# success,image = vidcap.read()

root = "output"
count = 0
total_frame = 99999999
path = os.path.join(root, 'rgb.txt')
image_size = (640, 480)

slam = Imaislam()
image = []
tframe = []
with open(path,'r') as f:
    for line in f.readlines():
        s = line.split(' ')
        t = s[1].split('\n')
        tframe.append(float(s[0]))
        pathtemp = os.path.join(root,t[0])
        im = cv2.imread(pathtemp)
        image.append(im)
        # print(s[0],pathtemp)


def add_value(array, new_value):
    array.append(float(new_value))
    array.pop(0)


path = 'output.txt'
index = 0
mavgX = [0,0,0,0,0]
mavgY = [0,0,0,0,0]
mavgZ = [0,0,0,0,0]
mavgF = [0,0,0,0,0]

# ---eddie 0315
# write frame to video
size = (im.shape[1], im.shape[0])
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter('slam_2022031401.avi', fourcc, 60, size)


with open(path, 'w') as f :
    for i in range(len(tframe)):
        now = datetime.now()
        millisecond = int(now.microsecond / 1000)
        formatted_time = now.strftime("%Y-%m-%d %H:%M:%S.{:03d}".format(millisecond))
        
        # ---eddie 0315
        # get the present delta
        speed = "{: 8.6f}".format(slam.trackmonocular(image[i],tframe[i]))
        X = "{: 8.6f}".format(slam.getdeltx())
        Y = "{: 8.6f}".format(slam.getdelty())
        Z = "{: 8.6f}".format(slam.getdeltz())
        F = "{: 8.6f}".format(slam.getdeltf())
        # calculate delta mavg
        add_value(mavgX, X)
        add_value(mavgY, Y)
        add_value(mavgZ, Z)
        add_value(mavgF, F)
        mavgSpeed = math.sqrt(pow(sum(mavgX),2)+pow(sum(mavgY),2)+pow(sum(mavgZ),2))/(sum(mavgF) + 0.0000001)        
        mavgSpeed = "{: 8.6f}".format(mavgSpeed)
        
        print('index = {}, speed = {}, mavg speed = {}, X = {}, Y = {}, Z = {}, F = {}'.format(index, speed, mavgSpeed, X, Y, Z, F))
        f.write('{}, {}, {}, {}, {}, {}, {}, {}\n'.format(index, formatted_time, speed, mavgSpeed, X, Y, Z, F))
        
        cv2.putText(image[i], "ind:" + str(index), (40, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.putText(image[i], "mavg speed:" + mavgSpeed, (40, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.putText(image[i], "speed:" + speed, (40, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

        out.write(image[i])
        index += 1