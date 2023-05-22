######################################################################
########################## Import libraries ##########################
######################################################################
import Car
import cv2
import matplotlib.pyplot as plt
import numpy as np
import os
import Paths
import requests
import Roads
import serial
import time
import torch

from pathlib import Path
from PIL import Image
from time import sleep

######################################################################
############################ Flask Setup #############################
######################################################################
# flask_....
url_ReceiveCall = 'http://172.26.34.12:777/send_to_eungR'
url_SendCoord = 'http://172.26.34.12:777/coordinate'
#url_ReceiveCall = 'http://172.26.16.25:1004/send_to_eungR'
#url_SendCoord = 'http://172.26.16.25:1004/coordinate'


######################################################################
############################# Path Setup #############################
######################################################################
path = Paths.Paths() # Create Path object


######################################################################
############################# Road Setup #############################
######################################################################
listRoads = Roads.Roads() # Create Roads object


######################################################################
##################### Stop Line Detection Setup ######################
######################################################################
#sld_.....
line_stop_y = 550 # const
line_stop_threshold = 3 # const
line_stop_num = 5 # const
line_stop_iterate = 0
line_stop_count = 0
line_stop_flag = False
y = 0
h = 0
flag_StopLine = False

######################################################################
######################### Intesection Setup ##########################
######################################################################
# ic_......
# 교차로에서 사용되는 변수


######################################################################
############################# LKAS Setup #############################
######################################################################
# lk_....
# Mask setting
polygon_default = np.array([[(0, 420), (0, 640), (480, 640), (480, 420), (480-200, 200), (200, 200)]], dtype=np.int32)
polygon = None
left_start_x = None
left_start_y = None
left_end_x = None # left_end_x will be used in planning section
left_end_y = None
right_start_x = None
right_start_y = None
right_end_x = None # right_end_x will be used in planning section
right_start_y = None

lower_yellow = np.array([20, 100, 100], dtype=np.uint8) # Lower threshold value for detecting yellow color
upper_yellow = np.array([30, 255, 255], dtype=np.uint8) # Upper threshold value for detecting yellow color
lower_white = np.array([0, 0, 200], dtype=np.uint8) # Lower threshold value for detecting white color
upper_white = np.array([255, 30, 255], dtype=np.uint8) # Upper threshold value for detecting white color
lower_orange = np.array([0, 100, 100], dtype=np.uint8)
upper_orange = np.array([22, 255, 255], dtype=np.uint8)
lower_orange2 = np.array([160, 100, 100], dtype=np.uint8)
upper_orange2 = np.array([180, 255, 255], dtype=np.uint8)
threshold_num = 5
threshold_left = False
threshold_right = False
lkas_iterate_count = 0
iterate_num = 10
threshold_count = 0
left_servo = False
right_servo = False
change = False
threshold_time = 0.25


def get_slope_intercept(lines): # This function finds the best line that fits all the small lines
    xs = []
    ys = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        xs.append(x1)
        xs.append(x2)
        ys.append(y1)
        ys.append(y2)
    coeffs = np.polyfit(xs, ys, deg=1, rcond=1e-6) # Perfrom linear regression
    slope = coeffs[0]
    intercept = coeffs[1]
    return slope, intercept


######################################################################
############################ 2D Map Setup ############################
######################################################################
# map_....
base_image = Image.open("./Image/Map.jpg") # Open the larger image
overlay_image1 = Image.open("./Image/Taxi1.png") # Open the smaller image
overlay_image2 = Image.open("./Image/Taxi2.png") # Open the smaller image
overlay_image3 = Image.open("./Image/Taxi3.png") # Open the smaller image
overlay_image4 = Image.open("./Image/Taxi4.png") # Open the smaller image


######################################################################
########################## Droidcam Setup ############################
######################################################################
cam = cv2.VideoCapture(1) # Connect to DroidCam client


######################################################################
######################### Bluetooth Setup ############################
######################################################################
"""
print("---------- Bluetooth setup ----------")
bt_cmd = None
port = "COM3"  # Port that is used to send signals to a connected RC car
bluetooth = serial.Serial(port, 9600)  # Connect to a RC car
bluetooth.flushInput()  # Clear Bluetooth input buffer
print("---------- Bluetooth setup complete ----------")
"""

######################################################################
############################# Time Setup #############################
######################################################################
startTime = None
endTime = None
servo_start_time = None
servo_end_time = None
time_to_flask = 0.1
ts_interval = 0.1


######################################################################
############################ 2D Map Setup ############################
######################################################################
# map_....
base_image = Image.open("./Image/Map.jpg") # Open the larger image
overlay_image1 = Image.open("./Image/Taxi1.png") # Open the smaller image
overlay_image2 = Image.open("./Image/Taxi2.png") # Open the smaller image
overlay_image3 = Image.open("./Image/Taxi3.png") # Open the smaller image
overlay_image4 = Image.open("./Image/Taxi4.png") # Open the smaller image


######################################################################
########################### R-Mutax Setup ############################
######################################################################
# map_....
# 2D map realated variables
initY = 930 # Initial Y coordinate of virtual Taxi
initX = 400 # Initial X coordinate of virtual Taxi
initD = 1 # Initial direction of Taxi
# Car system related variables
initM = 0 # Initial mode of Taxi. Do not change this value unless you are a developer
speed = 10 # Normal speed of Taxi. unit is (cm/s)
# Create taxi object
taxi = Car.Taxi()
taxi.setvmapYX(initY, initX)
taxi.setvcarYX(initY, initX)
taxi.setDirection(initD)
taxi.setMode(initM)


######################################################################
############################# V2V Setup ##############################
######################################################################
flag_IntersectionCar = False


######################################################################
########################### OD Flag Setup ############################
######################################################################

flag_StopCar = False
flag_StopSign = False
# flag_StopSign_first = False
# StopSign_count = 0


######################################################################
############################# YOLO Setup #############################
######################################################################
"""
print("---------- YOLO setup ----------")
threshold_confidence = 0.5
# yolo_iteration = 0
model_path = str(Path.cwd() / "yolov5s.pt") # Load YOLOv5
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True) # Load pretrained weight from Github
with open("coco.names", "r") as f: # Load COCO classes
    classes = [line.strip() for line in f.readlines()]
colors = np.random.uniform(0, 255, size=(len(classes), 3)) # Initialize random colors for detected bounding boxes
print("---------- YOLO setup complete ----------")
"""


######################################################################
########################### Begin R-Mutax ############################
######################################################################
print("System: Begin R-Mutax")
while True:    
    mode = taxi.getMode() # Get taxi mode
    ############################################################################
    ################################## mode 0 ##################################
    ############################################################################
    if mode == 0:
        print("System: Mode 0 started")
        # Tell R-Mutax to move from parking lot to road L
        bt_cmd = 'm'
        result_bytes = bt_cmd.encode('utf_8')
        #bt# bluetooth.write(result_bytes)
        ETA = 5 # Assumed that it will take 5 seconds for car to complete moving
        startTime = time.time()
        while True:
            # Show taxi front view
            ret, frame = cam.read()
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            cv2.imshow('Taxi Camera', frame)
            # Show map
            tempY, tempX = taxi.getvcarYX()
            canvas = Image.new("RGBA", base_image.size, (0, 0, 0, 0)) # Create canvas
            canvas.paste(base_image, (0, 0)) # Paste base image
            tempDir = taxi.getDirection()
            if tempDir == 1:
                canvas.paste(overlay_image1, (tempX, tempY), overlay_image1) # Paste overlaying image
            elif tempDir == 2:
                canvas.paste(overlay_image2, (tempX, tempY), overlay_image2)
            elif tempDir == 3:
                canvas.paste(overlay_image3, (tempX, tempY), overlay_image3)
            elif tempDir == 4:
                canvas.paste(overlay_image4, (tempX, tempY), overlay_image4)
            np_image = np.array(canvas) # Convert PIL to np
            cv_image=cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR) # Convert RGB to BGR
            cv2.namedWindow('Map', cv2.WINDOW_NORMAL)
            cv2.resizeWindow('Map', 800, 800)
            cv2.imshow('Map', cv_image) # Show map
            if cv2.waitKey(1) == ord('q'):
                break
            endTime = time.time()
            elapsedTime = endTime - startTime
            # 2D Map YX change
            taxi.setvcarY(int(initY - ((initY-760) * (elapsedTime / 5))))
            if elapsedTime > ETA:
                break
        print('now on the middle of road L')
        # Setting for mode 2
        # Taxi sysetm related setup
        taxi.setMode(2)
        taxi.setState(1) # car state: stop state (0->0)
        # Localization related setup
        infoRY, infoRX, infoRD, infoRN, info_real_road_Len = listRoads.getRealRoads(11)
        infoRX = infoRX + int(info_real_road_Len/2) # parking에서 도로 l로 나왔을 때 처음 x 좌표
        taxi.setrmapYX(infoRY, infoRX)
        taxi.setrcarYX(infoRY, infoRX)
        # 2D map related setup
        infoVY, infoVX, infoVD, infoVN, info_virtual_road_Len = listRoads.getVirtualRoads(11)
        infoVX = infoVX + int(info_virtual_road_Len/2) # parking에서 도로 l로 나왔을 때 처음 x 좌표 380, 225
        taxi.setvmapYX(infoVY, infoVX)
        taxi.setvcarYX(infoVY, infoVX)
        taxi.setDirection(infoVD)
        taxi.setDistance(info_real_road_Len/2) # Objective distance
        taxi.setDT(0) # DT = distance travelled
        taxi.setRoad('L') # Road name is 'L'
        # LKAS setup
        polygon = polygon_default
        print("---------- Mode 0 ended ----------")
    ############################################################################
    ################################## mode 1 ##################################
    ############################################################################
    elif mode == 1:
        new_road = True
        stop_road = False
        starting = taxi.getStarting()
        destination = taxi.getDestination()

        current_road = taxi.getRoad()
        cTOs = path.GPP(current_road, starting) # Current road to Starting
        # length_cTOs = len(cTOs)

        sTOd = path.GPP(starting, destination)
        # length_sTOd = len(sTOd)

        cur_path = cTOs
        # len_cur_path = length_cTOs

        time_to_flask = 1

        print("---------- Mode 1 started (part 1) ----------")
        # Begin mode 1 part 1
        while True:
            ######################################################################
            ############################# Perception #############################
            ######################################################################
            # Get frame from camera
            ret, frame = cam.read() # Read frame
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE) # Rotate frame 90 degrees clockwise
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV) # Change BGR -> HSV

            # Object detection (using YOLOv5)
            # yolov_results = model(frame) # Store result in 'yolov_results'
            
            # Stop Line Detecting
            orange_mask = cv2.inRange(hsv, lower_orange, upper_orange) + cv2.inRange(hsv, lower_orange2, upper_orange2)
            boxes, hierarchy=cv2.findContours(orange_mask,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
            
            #line_stop_iterate +=1
            y = 0
            h = 0
            for idx, box in enumerate(boxes):
                if idx==0:
                    continue
                x, y, w, h = cv2.boundingRect(box)
                if w > 100 and h < 50:  # 최소한의 넓이 조건을 충족하는 경우
                    x, y, w, h = cv2.boundingRect(box)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                    cv2.putText(frame, 'Stop Line', (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    if y + h > 630:
                        flag_StopLine = True
                    # if y >= line_stop_y:
                    #     if line_stop_flag == False:
                    #         line_stop_flag = True
                    #         line_stop_iterate = 1
                    #         line_stop_count = 1
                    #     else:
                    #        line_stop_count += 1            
            
            # LKAS
            yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow) # Create a yellow mask for detecing road lanes
            edges = cv2.Canny(yellow_mask, threshold1=50, threshold2=100, apertureSize=3) # Perform canny edge detection
            mask_roi = np.zeros_like(edges)
            cv2.fillPoly(mask_roi, polygon, 255)
            masked_edges = cv2.bitwise_and(edges, mask_roi)
            lines = cv2.HoughLinesP(masked_edges, rho=1, theta=np.pi / 180, threshold=20, minLineLength=50, maxLineGap=100)  # Perform hough Transform
            
            left_lines = [] # List used to store left lines that are detected
            right_lines = [] # List used to store right lines that are detected
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    if abs(y1 - y2) < 5: # y축과 거의 평행인 선
                        continue # 무시하고 for문 다시 돌아라
                    if x1 == x2:
                        continue
                    slope = (y2 - y1) / (x2 - x1)
                    if slope < 0:
                        left_lines.append(line)  # (0, 0) is upper-left corner of the image
                    else:
                        right_lines.append(line)
            
            left_xs = []
            left_ys = []
            right_xs = []
            right_ys = []

            for line in left_lines:
                x1, y1, x2, y2 = line[0]
                left_xs.extend([x1, x2])
                left_ys.extend([y1, y2])

            for line in right_lines:
                x1, y1, x2, y2 = line[0]
                right_xs.extend([x1, x2])
                right_ys.extend([y1, y2])

            
            if left_xs and left_ys and right_xs and right_ys:  # 탐지된 선이 있다면 if문 안 실행
                left_coeffs = np.polyfit(left_xs, left_ys, deg=1, rcond=1e-6)  # polyfit으로 왼쪽 선 구하기
                right_coeffs = np.polyfit(right_xs, right_ys, deg=1, rcond=1e-6)  # polyfit으로 오른쪽 선 구하기

                left_start_y = int(left_coeffs[1])
                left_start_x = 0  # 0은 기울기, 1은 절편
                left_end_y = int(frame.shape[0] * 0.4)  # 1 - 0.6 = 0.4 화면 height의 0.4 길이 만큼 선 그리기
                left_end_x = int((left_end_y - left_coeffs[1]) / left_coeffs[0])

                right_start_y = int(480*right_coeffs[0] + right_coeffs[1])
                right_start_x = 480
                right_end_y = int(frame.shape[0] * 0.4)
                right_end_x = int((right_end_y - right_coeffs[1]) / right_coeffs[0])

                # Draw detected lines
                cv2.line(frame, (left_start_x, left_start_y), (left_end_x, left_end_y), (0, 255, 0), thickness=5)
                cv2.line(frame, (right_start_x, right_start_y), (right_end_x, right_end_y), (0, 255, 0), thickness=5)
            
            ######################################################################
            ############################## Planning ##############################
            ######################################################################
            # Object detection
            class_ids = []
            confidences = []
            boxes = []
            #yolo_iteration += 1
            flag_StopSign = False
            """
            for yolov_result in yolov_results.xyxy[0]:
                label = classes[int(yolov_result[5])]
                confidence = yolov_result[4].item()
                if confidence > threshold_confidence:
                    x, y, x1, y1 = map(int, yolov_result[:4]) # slicing. get 0~3 elements
                    color = colors[int(yolov_result[5])]
                    cv2.rectangle(frame, (x, y), (x1, y1), color, 2)
                    cv2.putText(frame, f"{label}: {confidence:.2f}", (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            """
            # Stop Line Detecting
            # if line_stop_iterate == 5 and line_stop_flag == True:
            #     if line_stop_count >= line_stop_threshold:
            #         flag_StopLine = True
            #     line_stop_flag = False

            # LKAS
            lkas_iterate_count += 1
            if (left_end_x != None) and (right_end_x != None): # If lane detection was performed, then....
                if (left_end_x >500-right_end_x) and (threshold_right == False):  # If the car is tilted left
                    if threshold_left:  # 처음이 아닌 경우, 즉 count 중이라면
                        threshold_count += 1
                    else:  # 처음인 경우
                        threshold_left = True
                        threshold_count = 1
                        lkas_iterate_count = 1
                elif (left_end_x+20 < 480-right_end_x) and (threshold_left == False):  # If the car is tilted right
                    if threshold_right:
                        threshold_count += 1
                    else:
                        threshold_right = True
                        threshold_count = 1
                        lkas_iterate_count = 1
        
            if lkas_iterate_count == iterate_num: # Check if iterate count has reached iterate num
                if threshold_left:
                    if threshold_count >= threshold_num:  # 10번 반복하면서 5번 이상 탐지 성공했을 경우
                        right_servo = True  # 차량을 오른쪽으로 가게 만들어라 flag
                    threshold_left = False
                elif threshold_right:
                    if threshold_count >= threshold_num:  # 10번 반복하면서 5번 이상 탐지 성공했을 경우
                        left_servo = True  # 차량을 왼쪽으로 가게 만들어라 flag
                    threshold_right = False
            ###################################################################
            ################################# Check state #####################
            ###################################################################
            state = taxi.getState()
            if state == 1: # Stop 상태
                if (flag_StopLine): # 계속해서 멈춰있을 필요가 있는지 확인하기
                    print("Planning: car is stopped and still needs to stop")
                else: # 만약 계속 멈춰 있을 필요가 없다면 조건문 넣기  
                    taxi.setState(2)
                    taxi.setSpeed(speed)
                    print("Planning: car needs to go forward")
                
                # 지금 달리는 도로가 staring, 또는 destination일 경우
                if new_road:
                    new_road = False
                    current_road = taxi.getRoad()
                    if (current_road == starting) or (current_road == destination):
                        stop_road = True
            elif state == 2: # 0 -> 1
                print("")
            elif state == 3: # 1 -> 0
                taxi.setState(1) # 차 세워
                # 세 가지 케이스를 생각해볼 수 있다.
                # case 1 앞 차 때문에 멈춘 상황
                # case 2 목적지 도달한 경우 (픽업지, 도착지, 주차장)
                # case 3 정지선 도달한 경우
            elif state == 4: # 1 -> 1
                # RoI update
                if left_end_x:
                    if h != 0:
                        polygon = np.array([[(0, left_start_y - 80), (0, 640), (480, 640), (480, right_start_y - 80), (right_end_x + 10, y+h-10), (left_end_x - 10, y+h-10)]], dtype=np.int32)
                    else:
                        polygon = np.array([[(0, left_start_y - 80), (0, 640), (480, 640), (480, right_start_y - 80), (right_end_x + 10, right_end_y - 10), (left_end_x - 10, left_end_y - 10)]], dtype=np.int32)
                                
                # Localization 오차 보정도 나중에 추가하기
                if (flag_StopCar): # If there is a car infront of the Taxi. Taxi has to stop immediately
                    print('Planning: There is a car infront of the taxi')
                    taxi.setState(3)
                    taxi.setSpeed(0)
                elif (flag_StopLine): # If there is a stop line.
                    print('Planning: Stop line detected')
                    flag_StopLine = False
                    taxi.setState(5)
                    taxi.setSpeed(0)
                # Localization
                endTime = time.time()
                elapsedTime = endTime - startTime
                DT = elapsedTime*taxi.getSpeed()
                taxi.setDT(DT)
                # update YX
                infoRY, infoRX, infoRD, infoRN, info_real_road_Len = listRoads.getRealRoads(ord(taxi.getRoad())-65)
                infoVY, infoVX, infoVD, infoVN, info_virtual_road_Len = listRoads.getVirtualRoads(ord(taxi.getRoad())-65)
                ratio = info_virtual_road_Len / info_real_road_Len
                tempDir = taxi.getDirection()
                if tempDir == 1:
                    # real car
                    temprcarY = int(taxi.getrmapY() - DT)
                    taxi.setrcarY(temprcarY)
                    # virtual car
                    tempvcarY = int(taxi.getvmapY() - DT*ratio)
                    taxi.setvcarY(tempvcarY)
                elif tempDir == 2:
                    # real car
                    temprcarX = int(taxi.getrmapX() + DT)
                    taxi.setrcarX(temprcarX)
                    # virtual car
                    tempvcarX = int(taxi.getvmapX() + DT*ratio)
                    taxi.setvcarX(tempvcarX)
                elif tempDir == 3:
                    # real car
                    temprcarY = int(taxi.getrmapY() + DT)
                    taxi.setrcarY(temprcarY)
                    # virtual car
                    tempvcarY = int(taxi.getvmapY() + DT*ratio)
                    taxi.setvcarY(tempvcarY)
                elif tempDir == 4:
                    # real car
                    temprcarX = int(taxi.getrmapX() - DT)
                    taxi.setrcarX(temprcarX)
                    # virtual car
                    tempvcarX = int(taxi.getvmapX() - DT*ratio)
                    taxi.setvcarX(tempvcarX)
                
                # Send the coordinate of eungRitaxi to the Flask server every 1 second
                if elapsedTime > time_to_flask:
                    time_to_flask += 1
                    y, x = taxi.getvcarYX()
                    d = taxi.getDirection()
                    data = {'key1' : x, 'key2' : y, 'key3' : d}
                    response = requests.post(url_SendCoord, json=data)

                    if response.status_code == 200:
                        pass
                    else:
                        print("Fucking error: "+response.text)
                
                if (DT >= taxi.getDistance()): # 만약 도달을 했다면
                    taxi.setState(5) # 차 세워 당장!flag_StopLine = True # 사실 이거는 요기 있으면 안되고, 나중에 OD에서 해줘야 되는거지만.실험을 위해 넣어둠
                    print("Planning: Car is now at the stop line")
                if stop_road == True:
                    if DT >= (taxi.getDistance()/2):
                        # <<<요기>>> arduino stop code 넣기
                        sleep(5) # sleep for 5 seconds
                        # <<<요기>>> arduino forward code 넣기
                        startTime += 5 # since the program slept for 5 sec, we need to add 5 to startime
                        stop_road = False
            elif state == 5: # Taxi has arrived at the beginning of the intersection
                # Later, write code for checking if there are other cars that are on the intersection
                taxi.setState(6)

                current_road = taxi.getRoad()
                if current_road == starting:
                    cur_path = sTOd

                    nextRoad, nextRoadInt, nextRoadWay = path.nextRoad(current_road, cur_path)
                    taxi.setNextRoad(nextRoad)  # Next road's alphabet name
                    taxi.setNextRoadInt(nextRoadInt) # Next road's number
                    taxi.setNextRoadWay(nextRoadWay) # which way to go to get to next road 
                elif current_road == destination:
                    # randRoad사용
                    nextRoad, nextRoadInt, nextRoadWay = path.randRoad(current_road)
                    taxi.setNextRoad(nextRoad)  # Next road's alphabet name
                    taxi.setNextRoadInt(nextRoadInt) # Next road's number
                    taxi.setNextRoadWay(nextRoadWay) # which way to go to get to next road
                    # 그리고 주행 모드 2로 설정
                    taxi.setMode(2)
                    pass
                else: # 아직 path에서 갈 길이 남은 경우
                    nextRoad, nextRoadInt, nextRoadWay = path.nextRoad(current_road, cur_path)
                    taxi.setNextRoad(nextRoad)  # Next road's alphabet name
                    taxi.setNextRoadInt(nextRoadInt) # Next road's number
                    taxi.setNextRoadWay(nextRoadWay) # which way to go to get to next road 
            elif state == 6: # Taxi is starting to drive in the intersection
                pass
            elif state == 7: # Taxi has ended driving in intersection. Now back on road
                print('Planning: taxi has ended driving in the intersection')
                # Flag reset
                new_road = True
                # RoI reset
                polygon = polygon_default
                # Taxi sysetm related setup
                taxi.setState(1)
                # Localization related setup
                nextRoad = taxi.getNextRoad()
                taxi.setRoad(nextRoad)
                # Localization related setup
                infoRY, infoRX, infoRD, infoRN, info_real_road_Len = listRoads.getRealRoads(ord(nextRoad)-65)
                taxi.setDistance(info_real_road_Len)
                taxi.setDT(0)
                taxi.setrmapYX(infoRY, infoRX)
                taxi.setrcarYX(infoRY, infoRX)
                # 2D map related setup
                infoVY, infoVX, infoVD, infoVN, info_virtual_road_Len = listRoads.getVirtualRoads(ord(nextRoad)-65)
                taxi.setvmapYX(infoVY, infoVX)
                taxi.setvcarYX(infoVY, infoVX)
                taxi.setDirection(infoVD)

                if taxi.getMode() != 1: # Taxi state is 1, and mode is other than 2
                    break
        
            elif state == 8: # Taxi is driving in the intersection
                endTime = time.time()
                elapsedTime = endTime - startTime
                nextRoadWay = taxi.getNextRoadWay()
                if (nextRoadWay == 'turnLeft'): # If next way is left
                    if elapsedTime > 5:
                        print('Planning: arrived at next road')
                        taxi.setState(7)
                elif (nextRoadWay == 'turnRight'):
                    if elapsedTime > 5:
                        print('Planning: arrived at next road')
                        taxi.setState(7)
                elif (nextRoadWay == 'straight'):
                    if elapsedTime > 5:
                        print('Planning: arrived at next road')
                        taxi.setState(7)


            
            
            ######################################################################
            ############################## Control ###############################
            ######################################################################
            # 제어에서는, 시간 바꾸기, 제어 신호, State 변경만 가능
            # State sdjfl;sakdfj;alsdjfsdf djsfl
            state = taxi.getState()
            if state == 1: # 0 -> 1
                taxi.setSpeed(0)
                taxi.stop()
                ########수정!!@#!@#!@#!@#@#
            
            elif state == 2:
                taxi.moveForward()
                startTime = time.time()
                time_to_flask = 1
                taxi.setState(4)
                print("Control:car moving forward in road", taxi.getRoad())
            elif state == 3:
                print("")
            elif state == 4:
                if left_servo:
                    if change == False:  # 처음이라면
                        servo_start_time = time.time()
                        change = True
                        # make 응애 rc카 go left
                        print("turn left")
                        result = 'left'
                        result_bytes = result.encode('utf_8')
                        #bt# bluetooth.write(result_bytes)
                    else:  # 처음이 아니라면
                        servo_end_time = time.time()
                        servo_elapsed_time = servo_end_time - servo_start_time
                        if servo_elapsed_time >= threshold_time:
                            # make 응애 rc카 go straight
                            result = 'setup'
                            result_bytes = result.encode('utf_8')
                            #bt# bluetooth.write(result_bytes)
                            left_servo = False
                            change = False
                elif right_servo:
                    if change == False:  # 처음이라면
                        print("turn right")
                        servo_start_time = time.time()
                        change = True
                        # make 응애 rc카 go right
                        result = 'right'
                        result_bytes = result.encode('utf_8')
                        #bt# bluetooth.write(result_bytes)
                    else:  # 처음이 아니라면
                        servo_end_time = time.time()
                        servo_elapsed_time = servo_end_time - servo_start_time
                        if servo_elapsed_time >= threshold_time:
                            # make 응애 rc카 go straight
                            result = 'setup'
                            result_bytes = result.encode('utf_8')
                            #bt# bluetooth.write(result_bytes)
                            right_servo = False
                            change = False
            elif state == 5:
                taxi.stop()
                print('Control: stopped the car before entering the intersection')
            elif state == 6:
                nextRoadWay = taxi.getNextRoadWay()
                if (nextRoadWay == 'turnLeft'): # If next way is left
                    taxi.turnLeft()
                    print('Control: taxi is now turning left')
                elif (nextRoadWay == 'turnRight'):
                    taxi.turnRight()
                    print('Control: taxi is now turning right')
                elif (nextRoadWay == 'straight'):
                    taxi.straight()
                    print('Control: taxi is now going straight')
                taxi.setState(8) # Taxi driving in intersection
                startTime = time.time()
                print('Control: taxi now going into intersection')
            elif state == 7:
                taxi.stop()
            elif state == 8:
                pass
                
            ######################################################################
            ###################### Human-Machine Interface #######################
            ######################################################################
            # Show taxi camera with OD and LKAS results
            roi_mask_3ch = cv2.cvtColor(mask_roi, cv2.COLOR_GRAY2BGR)
            combined_result = cv2.addWeighted(frame, 0.8, roi_mask_3ch, 0.2, 0) # Combine OD image and LKAS image
            cv2.imshow('Taxi Camera', combined_result) # Show combined result

            # Show 2D map
            tempY, tempX = taxi.getvcarYX()
            canvas = Image.new("RGBA", base_image.size, (0, 0, 0, 0)) # Create canvas
            canvas.paste(base_image, (0, 0)) # Paste base image
            tempDir = taxi.getDirection()
            if tempDir == 1:
                canvas.paste(overlay_image1, (tempX, tempY), overlay_image1) # Paste overlaying image
            elif tempDir == 2:
                canvas.paste(overlay_image2, (tempX, tempY), overlay_image2)
            elif tempDir == 3:
                canvas.paste(overlay_image3, (tempX, tempY), overlay_image3)
            elif tempDir == 4:
                canvas.paste(overlay_image4, (tempX, tempY), overlay_image4)
            np_image = np.array(canvas) # Convert PIL to np
            cv_image=cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR) # Convert RGB to BGR
            cv2.namedWindow('Map', cv2.WINDOW_NORMAL) # Give a specific name to the window
            cv2.resizeWindow('Map', 800, 800) # Resize window size
            cv2.imshow('Map', cv_image) # Show 2D map
            
            if cv2.waitKey(1) == ord('q'): # Press Q to close the window. But window will pop back up in next iteration
                break

        print("---------- Mode 1 ended (part 1)----------")

    ############################################################################
    ################################## mode 2 ##################################
    ############################################################################
    elif mode == 2:
        print("---------- Mode 2 started ----------")
        # Mode 2 initialization setting
        threshold_left = False
        threshold_right = False
        lkas_iterate_count = 0
        threshold_count = 0
        # Line Stop Setting
        line_stop_iterate = 0
        line_stop_count = 0
        line_stop_flag = False

        # yolo_iteration = 0
        # flag_StopSign_first = False
        # StopSign_count = 0

        # Begin mode 2 while loop
        while True:
            ######################################################################
            ############################# Perception #############################
            ######################################################################
            # Get frame from camera
            ret, frame = cam.read() # Read frame
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE) # Rotate frame 90 degrees clockwise
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV) # Change BGR -> HSV

            # Object detection (using YOLOv5)
            # yolov_results = model(frame) # Store result in 'yolov_results'
            
            # Stop Line Detecting
            orange_mask = cv2.inRange(hsv, lower_orange, upper_orange) + cv2.inRange(hsv, lower_orange2, upper_orange2)
            boxes, hierarchy=cv2.findContours(orange_mask,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
            
            #line_stop_iterate +=1
            y = 0
            h = 0
            for idx, box in enumerate(boxes):
                if idx==0:
                    continue
                x, y, w, h = cv2.boundingRect(box)
                if w > 100 and h < 50:  # 최소한의 넓이 조건을 충족하는 경우
                    x, y, w, h = cv2.boundingRect(box)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                    cv2.putText(frame, 'Stop Line', (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    if y + h > 630:
                        flag_StopLine = True
                    # if y >= line_stop_y:
                    #     if line_stop_flag == False:
                    #         line_stop_flag = True
                    #         line_stop_iterate = 1
                    #         line_stop_count = 1
                    #     else:
                    #        line_stop_count += 1            
            
            # LKAS
            yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow) # Create a yellow mask for detecing road lanes
            edges = cv2.Canny(yellow_mask, threshold1=50, threshold2=100, apertureSize=3) # Perform canny edge detection
            mask_roi = np.zeros_like(edges)
            cv2.fillPoly(mask_roi, polygon, 255)
            masked_edges = cv2.bitwise_and(edges, mask_roi)
            lines = cv2.HoughLinesP(masked_edges, rho=1, theta=np.pi / 180, threshold=20, minLineLength=50, maxLineGap=100)  # Perform hough Transform
            
            left_lines = [] # List used to store left lines that are detected
            right_lines = [] # List used to store right lines that are detected
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    if abs(y1 - y2) < 5: # y축과 거의 평행인 선
                        continue # 무시하고 for문 다시 돌아라
                    if x1 == x2:
                        continue
                    slope = (y2 - y1) / (x2 - x1)
                    if slope < 0:
                        left_lines.append(line)  # (0, 0) is upper-left corner of the image
                    else:
                        right_lines.append(line)
            
            left_xs = []
            left_ys = []
            right_xs = []
            right_ys = []

            for line in left_lines:
                x1, y1, x2, y2 = line[0]
                left_xs.extend([x1, x2])
                left_ys.extend([y1, y2])

            for line in right_lines:
                x1, y1, x2, y2 = line[0]
                right_xs.extend([x1, x2])
                right_ys.extend([y1, y2])

            
            if left_xs and left_ys and right_xs and right_ys:  # 탐지된 선이 있다면 if문 안 실행
                left_coeffs = np.polyfit(left_xs, left_ys, deg=1, rcond=1e-6)  # polyfit으로 왼쪽 선 구하기
                right_coeffs = np.polyfit(right_xs, right_ys, deg=1, rcond=1e-6)  # polyfit으로 오른쪽 선 구하기

                left_start_y = int(left_coeffs[1])
                left_start_x = 0  # 0은 기울기, 1은 절편
                left_end_y = int(frame.shape[0] * 0.4)  # 1 - 0.6 = 0.4 화면 height의 0.4 길이 만큼 선 그리기
                left_end_x = int((left_end_y - left_coeffs[1]) / left_coeffs[0])

                right_start_y = int(480*right_coeffs[0] + right_coeffs[1])
                right_start_x = 480
                right_end_y = int(frame.shape[0] * 0.4)
                right_end_x = int((right_end_y - right_coeffs[1]) / right_coeffs[0])

                # Draw detected lines
                cv2.line(frame, (left_start_x, left_start_y), (left_end_x, left_end_y), (0, 255, 0), thickness=5)
                cv2.line(frame, (right_start_x, right_start_y), (right_end_x, right_end_y), (0, 255, 0), thickness=5)
            
            ######################################################################
            ############################## Planning ##############################
            ######################################################################
            # Object detection
            class_ids = []
            confidences = []
            boxes = []
            #yolo_iteration += 1
            flag_StopSign = False
            """
            for yolov_result in yolov_results.xyxy[0]:
                label = classes[int(yolov_result[5])]
                confidence = yolov_result[4].item()
                if confidence > threshold_confidence:
                    x, y, x1, y1 = map(int, yolov_result[:4]) # slicing. get 0~3 elements
                    color = colors[int(yolov_result[5])]
                    cv2.rectangle(frame, (x, y), (x1, y1), color, 2)
                    cv2.putText(frame, f"{label}: {confidence:.2f}", (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            """
            # Stop Line Detecting
            # if line_stop_iterate == 5 and line_stop_flag == True:
            #     if line_stop_count >= line_stop_threshold:
            #         flag_StopLine = True
            #     line_stop_flag = False

            # LKAS
            lkas_iterate_count += 1
            if (left_end_x != None) and (right_end_x != None): # If lane detection was performed, then....
                if (left_end_x >500-right_end_x) and (threshold_right == False):  # If the car is tilted left
                    if threshold_left:  # 처음이 아닌 경우, 즉 count 중이라면
                        threshold_count += 1
                    else:  # 처음인 경우
                        threshold_left = True
                        threshold_count = 1
                        lkas_iterate_count = 1
                elif (left_end_x+20 < 480-right_end_x) and (threshold_left == False):  # If the car is tilted right
                    if threshold_right:
                        threshold_count += 1
                    else:
                        threshold_right = True
                        threshold_count = 1
                        lkas_iterate_count = 1
        
            if lkas_iterate_count == iterate_num: # Check if iterate count has reached iterate num
                if threshold_left:
                    if threshold_count >= threshold_num:  # 10번 반복하면서 5번 이상 탐지 성공했을 경우
                        right_servo = True  # 차량을 오른쪽으로 가게 만들어라 flag
                    threshold_left = False
                elif threshold_right:
                    if threshold_count >= threshold_num:  # 10번 반복하면서 5번 이상 탐지 성공했을 경우
                        left_servo = True  # 차량을 왼쪽으로 가게 만들어라 flag
                    threshold_right = False

            # Check state
            state = taxi.getState()
            if state == 1: # Stop 상태
                if (flag_StopLine): # 계속해서 멈춰있을 필요가 있는지 확인하기
                    print("Planning: car is stopped and still needs to stop")
                    pass
                else: # 만약 계속 멈춰 있을 필요가 없다면 조건문 넣기  
                    taxi.setState(2)
                    taxi.setSpeed(speed)
                    print("Planning: car needs to go forward")
            elif state == 2: # 0 -> 1
                print("")
            elif state == 3: # 1 -> 0
                taxi.setState(1) # 차 세워
                # 세 가지 케이스를 생각해볼 수 있다.
                # case 1 앞 차 때문에 멈춘 상황
                # case 2 목적지 도달한 경우 (픽업지, 도착지, 주차장)
                # case 3 정지선 도달한 경우
            elif state == 4: # 1 -> 1
                # RoI update
                if left_end_x:
                    if h != 0:
                        polygon = np.array([[(0, left_start_y - 80), (0, 640), (480, 640), (480, right_start_y - 80), (right_end_x + 10, y+h-10), (left_end_x - 10, y+h-10)]], dtype=np.int32)
                    else:
                        polygon = np.array([[(0, left_start_y - 80), (0, 640), (480, 640), (480, right_start_y - 80), (right_end_x + 10, right_end_y - 10), (left_end_x - 10, left_end_y - 10)]], dtype=np.int32)
                
                
                
                # Localization 오차 보정도 나중에 추가하기
                if (flag_StopCar): # If there is a car infront of the Taxi. Taxi has to stop immediately
                    print('Planning: There is a car infront of the taxi')
                    taxi.setState(3)
                    taxi.setSpeed(0)
                elif (flag_StopLine): # If there is a stop line.
                    print('Planning: Stop line detected')
                    flag_StopLine = False
                    taxi.setState(5)
                    taxi.setSpeed(0)
                # Localization
                endTime = time.time()
                elapsedTime = endTime - startTime
                DT = elapsedTime*taxi.getSpeed()
                taxi.setDT(DT)
                # update YX
                infoRY, infoRX, infoRD, infoRN, info_real_road_Len = listRoads.getRealRoads(ord(taxi.getRoad())-65)
                infoVY, infoVX, infoVD, infoVN, info_virtual_road_Len = listRoads.getVirtualRoads(ord(taxi.getRoad())-65)
                ratio = info_virtual_road_Len / info_real_road_Len
                tempDir = taxi.getDirection()
                if tempDir == 1:
                    # real car
                    temprcarY = int(taxi.getrmapY() - DT)
                    taxi.setrcarY(temprcarY)
                    # virtual car
                    tempvcarY = int(taxi.getvmapY() - DT*ratio)
                    taxi.setvcarY(tempvcarY)
                elif tempDir == 2:
                    # real car
                    temprcarX = int(taxi.getrmapX() + DT)
                    taxi.setrcarX(temprcarX)
                    # virtual car
                    tempvcarX = int(taxi.getvmapX() + DT*ratio)
                    taxi.setvcarX(tempvcarX)
                elif tempDir == 3:
                    # real car
                    temprcarY = int(taxi.getrmapY() + DT)
                    taxi.setrcarY(temprcarY)
                    # virtual car
                    tempvcarY = int(taxi.getvmapY() + DT*ratio)
                    taxi.setvcarY(tempvcarY)
                elif tempDir == 4:
                    # real car
                    temprcarX = int(taxi.getrmapX() - DT)
                    taxi.setrcarX(temprcarX)
                    # virtual car
                    tempvcarX = int(taxi.getvmapX() - DT*ratio)
                    taxi.setvcarX(tempvcarX)
                
                # Send the coordinate of eungRitaxi to the Flask server every 1 second
                if elapsedTime > time_to_flask:
                    time_to_flask += 0.1
                    y, x = taxi.getvcarYX()
                    d = taxi.getDirection()
                    data = {'key1' : x, 'key2' : y, 'key3' : d}
                    response = requests.post(url_SendCoord, json=data)
                    #print(data)
                    if response.status_code == 200:
                        pass
                    else:
                        print("Fucking error: "+response.text)
                
                if (DT >= taxi.getDistance()): # 만약 도달을 했다면
                    taxi.setState(5) # 차 세워 당장!flag_StopLine = True # 사실 이거는 요기 있으면 안되고, 나중에 OD에서 해줘야 되는거지만.실험을 위해 넣어둠
                    print("Planning: Car is now at the stop line")
                
            elif state == 5: # Taxi has arrived at the beginning of the intersection
                # Later, write code for checking if there are other cars that are on the intersection
                # if (flag_IntersectionCar == False):
                taxi.setState(6)
                    

                # Check if there is a reservation
                response = requests.get(url_ReceiveCall) # request data from Flask server
                str1 = response.text # str1[0] is the starting node, str1[1] is the destination node
                
                if str1[0] != '0': # if we got something from the Flask server
                    starting = str1[0]
                    destination = str1[1]
                    print("Call received. From "+starting+" to "+destination)
                    taxi.setStarting(starting)
                    taxi.setDestination(destination)
                    taxi.setMode(1) # set Mode to 1 for autonomous RC taxi service

                    cTOs = path.GPP(taxi.getRoad(), starting)
                    nextRoad, nextRoadInt, nextRoadWay = path.nextRoad(taxi.getRoad(), cTOs)
                    taxi.setNextRoad(nextRoad)  # Next road's alphabet name
                    taxi.setNextRoadInt(nextRoadInt) # Next road's number
                    taxi.setNextRoadWay(nextRoadWay) # which way to go to get to next road 
                elif str1 == '00':
                    print("nah keep goin")
                    nextRoad, nextRoadInt, nextRoadWay = path.randRoad(taxi.getRoad())
                    taxi.setNextRoad(nextRoad)  # Next road's alphabet name
                    taxi.setNextRoadInt(nextRoadInt) # Next road's number
                    taxi.setNextRoadWay(nextRoadWay) # which way to go to get to next road

            elif state == 6: # Taxi is starting to drive in the intersection
                pass
            elif state == 7: # Taxi has ended driving in intersection. Now back on road
                print('Planning: taxi has ended driving in the intersection')
                # RoI reset
                polygon = polygon_default
                # Taxi sysetm related setup
                taxi.setState(1)
                # Localization related setup
                nextRoad = taxi.getNextRoad()
                taxi.setRoad(nextRoad)
                # Localization related setup
                infoRY, infoRX, infoRD, infoRN, info_real_road_Len = listRoads.getRealRoads(ord(nextRoad)-65)
                taxi.setDistance(info_real_road_Len)
                taxi.setDT(0)
                taxi.setrmapYX(infoRY, infoRX)
                taxi.setrcarYX(infoRY, infoRX)
                # 2D map related setup
                infoVY, infoVX, infoVD, infoVN, info_virtual_road_Len = listRoads.getVirtualRoads(ord(nextRoad)-65)
                taxi.setvmapYX(infoVY, infoVX)
                taxi.setvcarYX(infoVY, infoVX)
                taxi.setDirection(infoVD)

                if taxi.getMode() != 2: # Taxi state is 1, and mode is other than 2
                    break
        
            elif state == 8: # Taxi is driving in the intersection
                endTime = time.time()
                elapsedTime = endTime - startTime
                nextRoadWay = taxi.getNextRoadWay()
                if (nextRoadWay == 'turnLeft'): # If next way is left
                    if elapsedTime > 5:
                        print('Planning: arrived at next road')
                        taxi.setState(7)
                elif (nextRoadWay == 'turnRight'):
                    if elapsedTime > 5:
                        print('Planning: arrived at next road')
                        taxi.setState(7)
                elif (nextRoadWay == 'straight'):
                    if elapsedTime > 5:
                        print('Planning: arrived at next road')
                        taxi.setState(7)

            
            
            ######################################################################
            ############################## Control ###############################
            ######################################################################
            # 제어에서는, 시간 바꾸기, 제어 신호, State 변경만 가능
            state = taxi.getState()
            if state == 1: # 차 세워
                taxi.setSpeed(0)
                taxi.stop()
                ########수정!!@#!@#!@#!@#@#
            elif state == 2:
                taxi.moveForward()
                startTime = time.time()
                time_to_flask = ts_interval
                taxi.setState(4)
                print("Control:car moving forward in road", taxi.getRoad())
            elif state == 3:
                print("")
            elif state == 4:
                if left_servo:
                    if change == False:  # 처음이라면
                        servo_start_time = time.time()
                        change = True
                        # make 응애 rc카 go left
                        print("turn left")
                        result = 'left'
                        result_bytes = result.encode('utf_8')
                        #bt# bluetooth.write(result_bytes)
                    else:  # 처음이 아니라면
                        servo_end_time = time.time()
                        servo_elapsed_time = servo_end_time - servo_start_time
                        if servo_elapsed_time >= threshold_time:
                            # make 응애 rc카 go straight
                            result = 'setup'
                            result_bytes = result.encode('utf_8')
                            #bt# bluetooth.write(result_bytes)
                            left_servo = False
                            change = False
                elif right_servo:
                    if change == False:  # 처음이라면
                        print("turn right")
                        servo_start_time = time.time()
                        change = True
                        # make 응애 rc카 go right
                        result = 'right'
                        result_bytes = result.encode('utf_8')
                        #bt# bluetooth.write(result_bytes)
                    else:  # 처음이 아니라면
                        servo_end_time = time.time()
                        servo_elapsed_time = servo_end_time - servo_start_time
                        if servo_elapsed_time >= threshold_time:
                            # make 응애 rc카 go straight
                            result = 'setup'
                            result_bytes = result.encode('utf_8')
                            #bt# bluetooth.write(result_bytes)
                            right_servo = False
                            change = False
            elif state == 5:
                taxi.stop()
                print('Control: stopped the car before entering the intersection')
            elif state == 6:
                nextRoadWay = taxi.getNextRoadWay()
                if (nextRoadWay == 'turnLeft'): # If next way is left
                    taxi.turnLeft()
                    print('Control: taxi is now turning left')
                elif (nextRoadWay == 'turnRight'):
                    taxi.turnRight()
                    print('Control: taxi is now turning right')
                elif (nextRoadWay == 'straight'):
                    taxi.straight()
                    print('Control: taxi is now going straight')
                taxi.setState(8) # Taxi driving in intersection
                startTime = time.time()
                print('Control: taxi now going into intersection')
            elif state == 7:
                taxi.stop()
            elif state == 8:
                pass
                
            ######################################################################
            ###################### Human-Machine Interface #######################
            ######################################################################
            # Show taxi camera with OD and LKAS results
            roi_mask_3ch = cv2.cvtColor(mask_roi, cv2.COLOR_GRAY2BGR)
            combined_result = cv2.addWeighted(frame, 0.8, roi_mask_3ch, 0.2, 0) # Combine OD image and LKAS image
            cv2.imshow('Taxi Camera', combined_result) # Show combined result

            # Show 2D map
            tempY, tempX = taxi.getvcarYX()
            canvas = Image.new("RGBA", base_image.size, (0, 0, 0, 0)) # Create canvas
            canvas.paste(base_image, (0, 0)) # Paste base image
            tempDir = taxi.getDirection()
            if tempDir == 1:
                canvas.paste(overlay_image1, (tempX, tempY), overlay_image1) # Paste overlaying image
            elif tempDir == 2:
                canvas.paste(overlay_image2, (tempX, tempY), overlay_image2)
            elif tempDir == 3:
                canvas.paste(overlay_image3, (tempX, tempY), overlay_image3)
            elif tempDir == 4:
                canvas.paste(overlay_image4, (tempX, tempY), overlay_image4)
            np_image = np.array(canvas) # Convert PIL to np
            cv_image=cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR) # Convert RGB to BGR
            cv2.namedWindow('Map', cv2.WINDOW_NORMAL) # Give a specific name to the window
            cv2.resizeWindow('Map', 800, 800) # Resize window size
            cv2.imshow('Map', cv_image) # Show 2D map
            
            if cv2.waitKey(1) == ord('q'): # Press Q to close the window. But window will pop back up in next iteration
                break

cam.release()
cv2.destroyAllWindows()