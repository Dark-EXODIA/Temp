from Server import *
import time
MyServer=Server()
MyServer.newConnection()
MyServer.getRequiredActions()
while True:
    t0 = time.time()
    frame= MyServer.getNewFrame()
    objects= MyServer.detectObjects(frame)
    Alarms= MyServer.detectActions(objects)
    l=MyServer.SendAlarm(Alarms)
    if l==1:
        break
    t1 = time.time()
    #print(t1-t0)

