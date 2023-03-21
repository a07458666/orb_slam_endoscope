import cv2
import sys
sys.path.append('/home/aaeon/workspace/orb_slam_endoscope/ORB_SLAM3/lib/')
from imaislam import Imaislam
import matplotlib.pyplot as plt 
import os
import time 
from datetime import datetime
import math
import glob
import argparse

from trtInfer import TensorRTInfer
#video_path = './2022050601.mp4'
# video_path = '/home/aaeon/maskyolo/video/2022021501.mp4'
# vidcap = cv2.VideoCapture(video_path)
# success,image = vidcap.read()

def loadImage(root, txt_dir = 'rgb.txt'):
    path = os.path.join(root, txt_dir)
    
    images = []
    tframe = []
    with open(path,'r') as f:
        for line in f.readlines():
            if len(images) > 500:
                break
            try:
                s = line.split(' ')
                t = s[1].split('\n')
                tframe.append(float(s[0]))
                pathtemp = os.path.join(root, t[0])
                im = cv2.imread(pathtemp)
                images.append(im)
            except:
                print("invalid file path : ", line)
    return images, tframe


def add_value(array, new_value):
    array.append(float(new_value))
    array.pop(0)

def preprocess_image(input_img):
    img = input_img.copy()
    mean = [123.675, 116.28, 103.53]
    std = [58.395, 57.12, 57.375]
    img = cv.resize(img, (512,512))
    img = (img - mean) / std
    img = np.transpose(img, (2,0,1))
    img = torch.tensor(img)
    np_image = np.float32(img.numpy()) # Batch
    return np_image

def parse_args():
    parser = argparse.ArgumentParser('SLAM')
    parser.add_argument('--data_path', type=str, default='/home/aaeon/Downloads/output_A/')
    parser.add_argument('--save_path', type=str, default='slam_2022032101.avi')
    parser.add_argument('--output_txt_path', type=str, default='output.txt')
    parser.add_argument('--frontVelocity', type=bool, default=True)
    parser.add_argument('--depth', type=bool, default=True) # If you want to set false, the C code must also be modified
    parser.add_argument('--depth_engine_path', type=str, default="./simipu.trt")
    
    return parser.parse_args()

def main():
    args = parse_args()
    image, tframe = loadImage(args.data_path)
    
    if args.depth:
        trt_infer = TensorRTInfer(args.depth_engine_path)
        
    slam = Imaislam()
    
    index = 0
    mavgX = [0,0,0,0,0]
    mavgY = [0,0,0,0,0]
    mavgZ = [0,0,0,0,0]
    mavgF = [0,0,0,0,0]

    # ---eddie 0315
    # write frame to video
    size = (image[0].shape[1], image[0].shape[0])
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(args.save_path, fourcc, 60, size)
    

    with open(args.output_txt_path, 'w') as f :
        for i in range(len(tframe)):
            now = datetime.now()
            millisecond = int(now.microsecond / 1000)
            formatted_time = now.strftime("%Y-%m-%d %H:%M:%S.{:03d}".format(millisecond))
            
            # ---eddie 0315
            # get the present delta
            if args.depth:
                batcher_data = preprocess_image(image[i])
                out_trt = trt_infer.infer(batcher_data, top=1)
                out_trt = out_trt.reshape(1, 1, 512, 512)
                depthImage = np.squeeze(np.transpose(out_trt, (0, 2, 3, 1)))
                # out_trt  = out_trt / out_trt.max() * 255 
                # out_trt = cv2.cvtColor(out_trt, cv2.COLOR_RGB2BGR)
                # cv2.imwrite('./depth/simpit_trt_{i}.png', out_trt)
            
            speed = "{: 8.6f}".format(slam.track(image[i], depthImage, tframe[i], args.frontVelocity))
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
        
        
if __name__ == '__main__':
    main()