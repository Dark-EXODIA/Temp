from post_process import *
#test abandoned_luggage
det = [{"label":"luggage", "confidence": 0.56, "topleft": {"x": 184, "y": 101}, "bottomright": {"x": 274, "y": 382}, "framenum":1}]

det2 = [{"label":"luggage", "confidence": 0.56, "topleft": {"x": 200, "y": 120}, "bottomright": {"x": 300, "y": 400}, "framenum":2},
       {"label":"person", "confidence": 0.56, "topleft": {"x": 300, "y": 150}, "bottomright": {"x": 350, "y": 350}, "framenum":2}]
detect = post_process()
detect.abandoned_luggage(det)
detect.abandoned_luggage(det2)