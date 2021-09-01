import cv2

class Camera(object):
    def __init__(self):
        if cv2.__version__.startswith('2'):
            PROP_FRAME_WIDTH = cv2.CAP_PROP_FRAME_WIDTH
            PROP_FRAME_HEIGHT = cv2.CAP_PROP_FRAME_HEIGHT
        elif cv2.__version__.startswith('3'):
            PROP_FRAME_WIDTH = cv2.CAP_PROP_FRAME_WIDTH
            PROP_FRAME_HEIGHT = cv2.CAP_PROP_FRAME_HEIGHT
        else:
            PROP_FRAME_WIDTH = cv2.CAP_PROP_FRAME_WIDTH
            PROP_FRAME_HEIGHT = cv2.CAP_PROP_FRAME_HEIGHT

            self.camera_capture = cv2.VideoCapture(0)
            #self.camera_capture = cv2.VideoCapture(1)
            #self.camera_capture = cv2.VideoCapture(2)
            #self.camera_capture = cv2.VideoCapture(3)
            self.camera_capture.set(PROP_FRAME_WIDTH, 640)
            self.camera_capture.set(PROP_FRAME_HEIGHT, 480)
            #self.camera_capture.set(PROP_FRAME_WIDTH, 640)
            #self.camera_capture.set(PROP_FRAME_HEIGHT, 480)
            #self.camera_capture.set(PROP_FRAME_WIDTH, 640)
            #self.camera_capture.set(PROP_FRAME_HEIGHT, 480)
            #self.camera_capture.set(PROP_FRAME_WIDTH, 640)
            #self.camera_capture.set(PROP_FRAME_HEIGHT, 480)
            #self.camera_capture.set(PROP_FRAME_WIDTH, 640)
            #self.camera_capture.set(PROP_FRAME_HEIGHT, 480)


    def get_frame(self):
        success, image = self.camera_capture.read()
        ret, png = cv2.imencode('.png', image)
        return png.tostring()