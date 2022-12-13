import cv2
video_path = './2022050601.mp4'
vidcap = cv2.VideoCapture(video_path)
success,image = vidcap.read()
count = 0
total_frame = 99999999
path = './output/rgb.txt'
image_size = (640, 480)

with open(path, 'w') as f:
  f.write(f"video_path : {video_path}\n")
  f.write(f"total_frame : {total_frame}\n")
  f.write("=======\n")
  while success:
    if count >= total_frame:
    	break
    image = cv2.resize(image, image_size, interpolation=cv2.INTER_AREA)
    cv2.imwrite("./output/img/frame_%d.png" % count, image)     # save frame as JPEG file 
    frame_time = count / 30
    f.write(f"{frame_time} img/frame_%d.png\n" % count)     
    success,image = vidcap.read()
    print(f'Read {count} new frame: ', success)
    count += 1
