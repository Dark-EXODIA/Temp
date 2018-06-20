from darkflow.net.build import TFNet
from post_process import *
import cv2
import numpy as np

class Server:

    def __init__(self):
        options = {"model": "cfg/yolo.cfg", "load": "bin/yolov2.weights","gpu":1.0}
        self.tfnet = TFNet(options)
        self.detect = post_process()
        self.actions={}
        self.i=10
       
    def newConnection(self):
        #server code
        s=1+1
    def getRequiredActions(self):
        #server code
        self.actions['abandoned_luggage']=0   
        self.actions['car_parking']=1    
        self.actions['crowd']=0
        self.actions['weapon']=0
    def getNewFrame(self):
        #server code
        frame = cv2.imread("videos/image-"+str(self.i)+".png")
        self.i=self.i+1
        return frame

    def SendAlarm(self,Alarm):
        #server code   
        print("frame is "+str(self.i))
        if Alarm[0] != -1 or Alarm[1] != -1 or Alarm[2] != -1 or Alarm[3] != -1:
            print("Alarm!!!")
        print(Alarm)

    def detectObjects(self,frame) :
        result = self.tfnet.return_predict(frame)
        #print(result)
        return result
    def detectActions(self,objects):
        Alarm= np.zeros(4)
        if self.actions['abandoned_luggage']==1:
            detection=self.detect.abandoned_luggage(objects,self.i)
            Alarm[0]=detection
        if self.actions['car_parking']==1:
            detection=self.detect.car_parking(objects,self.i)
            Alarm[1]=detection

        if self.actions['crowd']==1:
            detection=self.detect.crowd(objects,self.i)
            Alarm[2]=detection

        if self.actions['weapon']==1:
            detection=self.detect.weapon(objects,self.i)
            Alarm[3]=detection
        return Alarm
        


   
        
