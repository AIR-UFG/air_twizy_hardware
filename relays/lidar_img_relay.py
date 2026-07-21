import rclpy, time
from sensor_msgs.msg import Image, CompressedImage
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
import numpy as np, cv2

SRC = {
  'range':  ('/ouster/range_image',  cv2.COLORMAP_TURBO),
  'signal': ('/ouster/signal_image', None),
  'nearir': ('/ouster/nearir_image', None),
  'reflec': ('/ouster/reflec_image', cv2.COLORMAP_BONE),
}
WIDTH=384; QUALITY=30; RATE=0.5   # fps por panorama (leve pra VPN)

rclpy.init(); node=rclpy.create_node('lidar_img_relay')
qos=QoSProfile(depth=1,reliability=ReliabilityPolicy.BEST_EFFORT,durability=DurabilityPolicy.VOLATILE)
pubs={}; last={}
def norm8(a):
    a=a.astype(np.float32); lo,hi=np.percentile(a,2),np.percentile(a,98)
    if hi<=lo: hi=lo+1
    return (np.clip((a-lo)/(hi-lo),0,1)*255).astype(np.uint8)
def mk(name, topic, cmap):
    pubs[name]=node.create_publisher(CompressedImage, topic+'/compressed', qos); last[name]=0.0
    def cb(msg):
        now=time.time()
        if now-last[name] < 1.0/RATE: return
        last[name]=now
        h,w=msg.height,msg.width; b=np.frombuffer(bytes(msg.data),dtype=np.uint8)
        try:
            if msg.encoding in ('mono16','16UC1'): a=b.view('<u2')[:h*w].reshape(h,w)
            elif msg.encoding in ('mono8','8UC1'): a=b.reshape(h,w)
            elif msg.encoding in ('32FC1',):       a=b.view('<f4')[:h*w].reshape(h,w)
            else:                                  a=b.reshape(h,w,-1)[:,:,0]
        except Exception: return
        g=norm8(a.astype(np.float32))
        img=cv2.applyColorMap(g,cmap) if cmap is not None else cv2.cvtColor(g,cv2.COLOR_GRAY2BGR)
        img=cv2.resize(img,(WIDTH, h*2), interpolation=cv2.INTER_NEAREST)
        ok,enc=cv2.imencode('.jpg',img,[cv2.IMWRITE_JPEG_QUALITY,QUALITY])
        if not ok: return
        out=CompressedImage(); out.header=msg.header; out.format='jpeg'; out.data=enc.tobytes()
        pubs[name].publish(out); print(name, len(out.data), 'bytes', flush=True)
    node.create_subscription(Image, topic, cb, qos)
for n,(t,c) in SRC.items(): mk(n,t,c)
print('lidar_img_relay up', flush=True)
rclpy.spin(node)
