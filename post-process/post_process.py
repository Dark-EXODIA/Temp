#format of detection {"label":"person", "confidence": 0.56, "topleft": {"x": 184, "y": 101}, "bottomright": {"x": 274, "y": 382}}
import math
fps = 5 #fps of video
k = 60 * fps #time allowed for luggage to be alone in sec
k_car = 4 * fps #time allowed for car to stop in sec
k_crowd = 5 * fps
s = 1 * fps
d = 0.5 #ratio between height of person and distance allowed between person and luggage
iou_threshold=0.8
crowd_threshold=0

weapon_confidence = 0.1
people_confidence = 0.3
luggage_confidence = 0.3
vehicle_confidence = 0.3


class post_process:
  def __init__(self):
    self.past_luggage = []
    self.past_cars = []
    self.crowdAlarm = 0
    self.no_crowd = 0
    self.weaponAlarm = 0
    self.no_weapon = 0
    self.carAlarm = 0
    self.no_car = 0
    self.luggageAlarm = 0
    self.no_luggage = 0
    self.weapon_frameno = 0
    self.crowd_frameno = 0
    self.crowd_timer=0
    self.weapon_timer=0
  def setCarwait (self,k):
    global k_car
    k_car = k * fps #time allowed for car to stop in sec
  def setperson (self,person):
    global crowd_threshold
    crowd_threshold = person
  def iou(self,o1, o2):
    o1_x1 = o1['topleft']['x']
    o1_y1 = o1['topleft']['y']
    o1_x2 = o1['bottomright']['x']
    o1_y2 = o1['bottomright']['y']

    o2_x1 = o2['topleft']['x']
    o2_y1 = o2['topleft']['y']
    o2_x2 = o2['bottomright']['x']
    o2_y2 = o2['bottomright']['y']

    intersection_x1 = max(o1_x1, o2_x1)
    intersection_x2 = min(o1_x2, o2_x2)
    intersection_y1 = max(o1_y1, o2_y1)
    intersection_y2 = min(o1_y2, o2_y2)
    if intersection_x1 > intersection_x2 or intersection_y1 > intersection_y2:
      return 0
    intersection = (intersection_x2 - intersection_x1) * (intersection_y2 - intersection_y1)
    area1 = (o1_x2-o1_x1) * (o1_y2-o1_y1)
    area2 = (o2_x2-o2_x1) * (o2_y2-o2_y1)
    union = area1 + area2 - intersection
    iou = 1.0*intersection / union
    #print("iou:",iou)
    return iou
  #################################################################################################################################

#get center of object detected. x has to be of detection format
  def center(self,x):
    center = {}
    center['x'] = (x['bottomright']['x'] - x['topleft']['x']) / 2 + x['topleft']['x'] 
    center['y'] = (x['bottomright']['y'] - x['topleft']['y']) / 2 + x['topleft']['y']
    #print("Center:", center['x'], center['y'])
    return center
  #################################################################################################################################
#get height of person. person is of known format
  def height(self,person):
    height = person['bottomright']['y'] - person['topleft']['y']
    #print("height:",height)
    return height
  #################################################################################################################################
#get distance between 2 centers (points) using euclidean distance: d = sqrt((x2-x1)^2+(y2-y1)^2)
  def distance(self,p1, p2):
    distance = math.sqrt((p1['x']-p2['x'])**2 +(p1['y']-p2['y'])**2)
    #print("distance:",distance)
    return  distance 
  #################################################################################################################################
	
  def diameter (self, obj):
    dim = (obj['bottomright']['x'] - obj['topleft']['x']) / 2
    #print("Diameter", dim)
    return dim
  #################################################################################################################################
#check if there exists a person such that the distance between luggage and person is <= distance threshold
#(which is d * height of person)
  def isPersonNear(self,luggage, people):
    for p in people:
      if self.distance(self.center(luggage), self.center(p)) - self.diameter(luggage) - self.diameter(p) <= d * self.height(p)  :
        print("Person is near")
        return 1
    print("No person is near")
    return 0
  #################################################################################################################################

# checks if this luggage exists in past_luggage and takes approperiate action
#we check if same luggage by iou >= threshold
#if true reset not_detected (used to remove luggage that hasn't been seen for a while)then check if time allowed for
#left luggage has been exceeded and return
  #returns:
  #1 if luggage remains longer than k in same spot
  #2 if luggae in same spot but didn't exceed k
  #0 if luggage is not in past_luggage
  def isOverdueLuggage(self,luggage, inc_time):
    idx = -1
    for l in self.past_luggage:
      idx+=1
      if self.iou(l, luggage) >= iou_threshold:
        l['notDetected']=0        
        if idx not in inc_time:
          inc_time.append(idx)
        if l['time'] > k:
          print("Exceeded alone time")
          return (1, l['frameno'])
        print("Didn't Exceed alone time")
        return (2, l['frameno'])
    print("Didn't find luggage in past")
    return (0,-1)
  #################################################################################################################################

#same as isOverdueLuggage
  def isOverdueCar(self,car, inc_time):
    idx = -1
    for c in self.past_cars:
      idx+=1
      if self.iou(c, car) >= iou_threshold:
        c['notDetected']=0
        if idx not in inc_time:
          inc_time.append(idx)
        if c['time'] > k_car:
            print("Car exceeded allowed time")
            return (1, c['frameno'])
        print("Car didn't exceed allowed time")
        return (2, c['frameno'])
    print("Didn't find car in past")
    return (0,-1)
  #################################################################################################################################

  #method to detect luggage that has been abandoned (i.e. no person near it) for some time k
  #Procedure:
  #increase 'notDetected' time for all past_luggage (later to be reset if detected)
  #extract people detections and luggage detections into separate lists
  #for every luggage detected in this frame, check whether a person is near it (i.e. distance between luggage and person < d). if true skip this luggage
  #otherwise check if it is in past_luggage (has iou with one in past_luggage > threshold) and has surpassed k (time allowed for any luggage to be alone) if true alert
  #if luggage in past_lugage but didn't exceed k increment its time and return
  #if luggage isn't in past_luggage add it
  #check for all past_luggage if any hasn't been detected for a certain period then remove it from past_luggage
  def abandoned_luggage(self,detections, frameno):
    cur_people = []
    cur_luggage = []
    inc_lug_time = []
    due_lugagge_frameno_start = -1
    for l in self.past_luggage:
      l['notDetected']+=1
    for i in detections:
      if i['label'] == "person" and i['confidence'] >= people_confidence:
        cur_people.append(i)
      elif i['label'] == "luggage" and i['confidence'] >= luggage_confidence:
        cur_luggage.append(i)
    print("Found", len(cur_people), "people and", len(cur_luggage), "luggage")
    #for every current luggage detected
    for l in cur_luggage:
      #if person near it, then not abandoned, skip
      if self.isPersonNear(l, cur_people)==1:
        continue
      #if no person near it check if it's overdue
      ret,ret_frameno = self.isOverdueLuggage(l,inc_lug_time)
      #if yes, then get minimum start of overdue lug 
      if ret==1:
        if due_lugagge_frameno_start == -1 or ret_frameno < due_lugagge_frameno_start:
            due_lugagge_frameno_start = ret_frameno
      #if lug doesn't exist in past lug then add it to them
      if ret == 0: 
        l['time']=1
        l['notDetected']=0
        l['frameno']=frameno
        self.past_luggage.append(l)
    #increment every lug that should be incremented
    for i in inc_lug_time:
      print("increasing time of car ", i)
      self.past_luggage[i]['time'] += 1
    #try to turn off alarm
    turn_alarm_off = 1
    idx = -1
    for l in self.past_luggage:
      idx+=1
      #if car hasn't been detected for RE then remove it
      if l['notDetected'] > s:
        print("removing luggage", idx)
        del self.past_luggage[idx]
      #if not removed and its overdue, we can't trun off alarm so reset it
      elif c['time'] > k:
        turn_alarm_off = 0
    #if alarm is off and we have an overdue car then turn on alarm and return its start
    if self.luggageAlarm == 0 and due_luggage_frameno_start != -1:
        self.luggageAlarm = 1
        return (0, due_luggage_frameno_start)
    #if alarm should be turned off then this is end of action so return frameno 
    if turn_alarm_off == 1:
        self.luggageAlarm = 0
        return (1, frameno)
    return (-1,-1)
  #################################################################################################################################
#same as abandoned_luggage
  def car_parking(self,detections, frameno):
    cur_cars = []
    inc_car_time = []
    due_car_frameno_start= -1
    for c in self.past_cars:
      c['notDetected']+=1
    for d in detections:
      print(d['label'])
      if d['label'] == "vehicle" and i['confidence'] >= vehicle_confidence:
        cur_cars.append(d)
    print("Found", len(cur_cars), "car(s)")
    #for every car detected in this frame

    for c in cur_cars:
      #check if car is parked
      ret,ret_frameno = self.isOverdueCar(c,inc_car_time)
      #get frameno of earliest car that is overdue
      if ret==1:
        self.no_car = 0
        if due_car_frameno_start == -1 or ret_frameno < due_car_frameno_start:
            due_car_frameno_start = ret_frameno
      #car wasn't found in past, new car so add to past and intialize values
      if ret == 0: 
        c['time']=1
        c['notDetected']=0
        c['frameno']=frameno
        self.past_cars.append(c)
    #every car that was detected this frame, increment its time
    for i in inc_car_time:
      self.past_cars[i]['time'] += 1
     
    idx = -1
    #try to turn alarm off
    turn_alarm_off = 1
    for c in self.past_cars:
      idx+=1
      #remove any car that hasn't been detected for RE 
      if c['notDetected'] > s:
        print("removing car", idx)
        del self.past_cars[idx]
      #if car not removed and it's overdue, then can't turn off alarm so reset it
      elif c['time'] > k_car:
          turn_alarm_off = 0
    #if alarm is off and a car is now over due os turn alarm on and return start frameno of this car
    if self.carAlarm == 0 and due_car_frameno_start != -1:
        self.carAlarm = 1
        return (0, due_car_frameno_start)
    #if alarm can be turned off turn it off and return current frameno as this is end of action
    if turn_alarm_off == 1:
        self.carAlarm = 0
        return (1, frameno)
    return (-1,-1)
  #################################################################################################################################
  def crowd(self,detections, frameno):
      cnt = 0
      for d in detections:
        if d['label'] == "person" and i['confidence'] >= people_confidence:
          cnt+=1
      print("Found", cnt, "people")
      #if count of people in current frame > crowd_threshold, then increment crowd_timer and reset no_crowd timer to 0
      if cnt >= crowd_threshold:
        self.crowd_timer += 1
        self.no_crowd = 0
        #if crowd timer > interval allowed for crowd and alarm is off, raise alarm and return start frame no
        if self.crowd_timer > k_crowd and self.crowdAlarm == 0:
          self.crowdAlarm=1
          return (0, self.crowd_frameno)
        #else if this is first frame where crowd is detected, mark start frameno of crowd as this frameno
        elif self.crowd_timer == 1:
          self.crowd_frameno = frameno
      #if cnt < crowd_threshold then increment no_crowd timer
      if cnt < crowd_threshold:
        self.no_crowd += 1
      #if cnt < crowd_threshold and noCrowd timer > RE, then reset crowdAlarm, no_crowd and crowdTimer
      if cnt < crowd_threshold and self.no_crowd > s:
        self.no_crowd = 0
        self.crowd_timer = 0
        #if alarm is going from on to off, this is end of action return current frameno
        if crowdAlarm == 1:
          self.crowdAlarm=0
          return (1, frameno)    
        self.crowdAlarm=0
      return (-1,-1)
  #################################################################################################################################    
  def weapon(self,detections, frameno):
      weapon = 0
      for d in detections:
        if d['label'] == "weapon" and i['confidence'] >= weapon_confidence:
          weapon=1
      print("Found weapon")
      #if a weapon is detected in current frame
      if weapon == 1:
        #increase weapon timer by 1
        self.weapon_timer += 1
        #reset no_Weapon to 0
        self.no_weapon = 0
        #if time of weapon detected > RE and alarm isn't on, raise alarm and return starting frame no.
        if self.weapon_timer > s and self.weaponAlarm == 0:
          self.weaponAlarm=1
          return (0, self.weapon_frameno)
        #else if this is first frame of weapon detection then save its number as start frame  
        elif self.weapon_timer == 1:
          self.weapon_frameno = frameno
      #if no weapon is detected in this frame and alarm is on, then increase no_weapon timer by 1
      if weapon == 0 and self.weaponAlarm == 1:
        self.no_weapon += 1 
      #if no weapon is detected and no_weapon timer is > RE then we need to stop alarm and reset weapon_timer
      if weapon == 0 and self.no_weapon > s:
        self.no_weapon = 0
        self.weapon_timer = 0
        if self.weaponAlarm == 1:
            self.weaponAlarm = 0
            return (1, frameno)
        self.weaponAlarm=0
      return (-1,-1)
	
######################################################################
