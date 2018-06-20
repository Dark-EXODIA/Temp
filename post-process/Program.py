from Server import *
MyServer=Server()
MyServer.newConnection()
MyServer.getRequiredActions()
while True:
    frame= MyServer.getNewFrame()
    objects= MyServer.detectObjects(frame)
    Alarms= MyServer.detectActions(objects)
    MyServer.SendAlarm(Alarms)
