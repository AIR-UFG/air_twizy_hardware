import rclpy, time
from sensor_msgs.msg import Image, CompressedImage
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
import numpy as np, cv2

CAMS = {
  'top_left':'/camera/top_left/image_raw',
  'top_front':'/camera/top_front/image_raw',
  'top_right':'/camera/top_right/image_raw',
}
WIDTH=320; QUALITY=40; RATE=1.0   # fps por camera

rclpy.init(); node=rclpy.create_node('cam_compress_relay')
qos=QoSProfile(depth=1,reliability=ReliabilityPolicy.BEST_EFFORT,durability=DurabilityPolicy.VOLATILE)
pubs={}; last={}
def mk(name, topic):
    pubs[name]=node.create_publisher(CompressedImage, topic+'/compressed', qos)
    last[name]=0.0
    def cb(msg):
        now=time.time()
        if now-last[name] < 1.0/RATE: return
        last[name]=now
        h,w=msg.height,msg.width
        buf=np.frombuffer(bytes(msg.data),dtype=np.uint8)
        try:
            if msg.encoding in ('bayer_rggb8','bayer_rg8'):
                img=cv2.cvtColor(buf.reshape(h,w),cv2.COLOR_BayerBG2BGR)
            elif msg.encoding=='rgb8':
                img=cv2.cvtColor(buf.reshape(h,w,3),cv2.COLOR_RGB2BGR)
            elif msg.encoding=='bgr8':
                img=buf.reshape(h,w,3)
            elif msg.encoding=='mono8':
                img=cv2.cvtColor(buf.reshape(h,w),cv2.COLOR_GRAY2BGR)
            else:
                return
        except Exception:
            return
        img=cv2.resize(img,(WIDTH,int(WIDTH*h/w)))
        img=cv2.rotate(img,cv2.ROTATE_180)
        ok,enc=cv2.imencode('.jpg',img,[cv2.IMWRITE_JPEG_QUALITY,QUALITY])
        if not ok: return
        out=CompressedImage(); out.header=msg.header; out.format='jpeg'; out.data=enc.tobytes()
        pubs[name].publish(out)
        print(name,'->',len(out.data),'bytes',flush=True)
    node.create_subscription(Image, topic, cb, qos)
for n,t in CAMS.items(): mk(n,t)
print('relay up',flush=True)
rclpy.spin(node)
