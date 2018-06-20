#format of detection {"label":"person", "confidence": 0.56, "topleft": {"x": 184, "y": 101}, "bottomright": {"x": 274, "y": 382}}
import math
fps = 30 #fps of video
k = 60  #time allowed for luggage to be alone in sec
k_car = 60 * fps #time allowed for car to stop in sec
s = 2 * fps
d = 0.5 #ratio between height of person and distance allowed between person and luggage
iou_threshold=0.8
crowd_threshold=20

class post_process:
  def __init__(self):
    self.past_luggage = []
    self.past_cars = []
    self.crowdAlarm = 0
    self.no_crowd = 0
    self.weaponAlarm = 0
    self.no_weapon = 0
    self.weapon_frameno = 0
    self.crowd_timer=0
    self.weapon_timer=0
#Get iou betweenm 2 objects. o1 and o2 have to be of detection format
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

#get center of object detected. x has to be of detection format
  def center(self,x):
    center = {}
    center['x'] = (x['bottomright']['x'] - x['topleft']['x']) / 2 + x['topleft']['x'] 
    center['y'] = (x['bottomright']['y'] - x['topleft']['y']) / 2 + x['topleft']['y']
    #print("Center:", center['x'], center['y'])
    return center
#get height of person. person is of known format
  def height(self,person):
    height = person['bottomright']['y'] - person['topleft']['y']
    #print("height:",height)
    return height
#get distance between 2 centers (points) using euclidean distance: d = sqrt((x2-x1)^2+(y2-y1)^2)
  def distance(self,p1, p2):
    distance = math.sqrt((p1['x']-p2['x'])**2 +(p1['y']-p2['y'])**2)
    #print("distance:",distance)
    return  distance 
	
  def diameter (self, obj):
    dim = (obj['bottomright']['x'] - obj['topleft']['x']) / 2
    #print("Diameter", dim)
    return dim
#check if there exists a person such that the distance between luggage and person is <= distance threshold
#(which is d * height of person)
  def isPersonNear(self,luggage, people):
    for p in people:
      if self.distance(self.center(luggage), self.center(p)) - self.diameter(luggage) - self.diameter(p) <= d * self.height(p)  :
        #print("Person is near")
        return 1
    #print("No person is near")
    return 0

# checks if this luggage exists in past_luggage and takes approperiate action
#we check if same luggage by iou >= threshold
#if true reset not_detected (used to remove luggage that hasn't been seen for a while)then check if time allowed for
#left luggage has been exceeded if true set flag to true (we alerted don't alert again for this) and return
# if flag 'alert' is true don't alert if time hasn't passed return
  #returns:
  #1 if luggage remains longer than k in same spot
  #2 if luggae in same spot but didn't exceed k or already alerted
  #0 if luggage is not in past_luggage
  def isOverdueLuggage(self,luggage):
    idx = -1
    for l in self.past_luggage:
      idx+=1
      if self.iou(l, luggage) >= iou_threshold:
        l['notDetected']=0
        l['time']+=1
        if l['time'] > k:
          if l['alert']==0:
            print("Exceeded alone time and didn't alert")
            c['alert']=1
            return 1
          print("Exceeded alone time but alerted")
          return 2
        print("found item in past_luggage")
        return 2
    print("Didn't find luggage in past")
    return 0

#same as isOverdueLuggage
  def isOverdueCar(self,car):
    idx = -1
    for c in self.past_cars:
      idx+=1
      if self.iou(c, car) >= iou_threshold:
        c['notDetected']=0
        c['time']+=1
        if c['time'] > k_car:
          if c['alert']==0:
            print("Exceeded stop time and didn't alert")
            c['alert']=1
            return 1
          print("Exceeded stop time but alerted")
          return 2
        print("found car in past_cars")
        return 2
    print("Didn't find car in past")
    return 0

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
    for l in self.past_luggage:
      l['notDetected']+=1
    for i in detections:
      if i['label'] == "person":
        cur_people.append(i)
      elif i['label'] == "luggage":
        cur_luggage.append(i)
    print("Found", len(cur_people), "people and", len(cur_luggage), "luggage")
    for l in cur_luggage:
      if self.isPersonNear(l, cur_people)==1:
        continue
      ret = self.isOverdueLuggage(l)
      if ret==1:
        return l['frameno']
      if ret == 0: 
        l['time']=1
        l['notDetected']=0
        l['alert']=0
        l['frameno']=frameno
        self.past_luggage.append(l)
    idx = -1
    for l in self.past_luggage:
      idx+=1
      if l['notDetected'] > s:
        print("removing luggage", idx)
        del self.past_luggage[idx]
    return -1
#same as abandoned_luggage
  def car_parking(self,detections, frameno):
    cur_cars = []
    for c in self.past_cars:
      c['notDetected']+=1
    for d in detections:
      if d['label'] == "car":
        cur_cars.append(d)
    print("Found", len(cur_cars), "car(s)")
    for c in cur_cars:
      ret = self.isOverdueCar(c)
      if ret==1:
        return c['frameno']
      if ret == 0: 
        c['time']=1
        c['notDetected']=0
        c['alert']=0
        c['frameno']=0
        self.past_cars.append(c)
    idx = -1
    for c in self.past_cars:
      idx+=1
      if c['notDetected'] > s:
        print("removing car", idx)
        del self.past_cars[idx]
    return -1
  def crowd(self,detections, frameno):
      cnt = 0
      for d in detections:
        if d['label'] == "person":
          cnt+=1
      print("Found", cnt, "people")
      if cnt > crowd_threshold:
        self.crowd_timer += 1
        self.no_crowd = 0
        if self.crowd_timer > s and self.crowdAlarm == 0:
          self.crowdAlarm=1
          return self.crowd_frameno
        elif self.crowd_timer == 1:
          self.crowd_frameno = frameno
      if cnt <= crowd_threshold:
        self.no_crowd += 1
      if cnt <= crowd_threshold and self.no_crowd > s:
        self.crowdAlarm=0
        self.no_crowd = 0
        self.crowd_timer = 0
      return -1
  def weapon(self,detections, frameno):
      weapon = 0
      for d in detections:
        if d['label'] == "weapon":
          weapon=1
      print("Found weapon")
      if weapon == 1:
        self.weapon_timer += 1
        self.no_weapon = 0
        if self.weapon_timer > s and self.weaponAlarm == 0:
          self.weaponAlarm=1
          return self.weapon_frameno
        elif self.crowd_timer == 1:
          self.crowd_frameno = frameno
      if weapon == 0:
        self.no_weapon += 1
      if weapon == 0 and self.no_weapon > s:
        self.weaponAlarm=0
        self.no_weapon = 0
        self.weapon_timer = 0
      return -1
	
######################################################################
