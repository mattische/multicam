import sys, time, subprocess, argparse, numpy as np, onnxruntime as ort
p=argparse.ArgumentParser()
p.add_argument('--dev',default='/dev/video2'); p.add_argument('--w',type=int,default=640); p.add_argument('--h',type=int,default=480)
p.add_argument('--fps',type=int,default=30); p.add_argument('--ratio',type=float,default=0.25)
p.add_argument('--threads',type=int,default=4); p.add_argument('--seconds',type=float,default=0)
p.add_argument('--model',default='rvm_mobilenetv3_fp32.onnx'); p.add_argument('--bench',action='store_true')
p.add_argument('--dump',default=''); p.add_argument('--bg',default='')
a=p.parse_args(); t0=time.time()
so=ort.SessionOptions(); so.intra_op_num_threads=a.threads
s=ort.InferenceSession(a.model,so,providers=['CPUExecutionProvider'])
W,H=a.w,a.h
cam=subprocess.Popen(['ffmpeg','-loglevel','error','-f','v4l2','-input_format','yuyv422','-video_size',f'{W}x{H}','-framerate',str(a.fps),'-i',a.dev,'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
rec=[np.zeros((1,1,1,1),np.float32)]*4; ratio=np.array([a.ratio],np.float32)
n=0; times=[]; first=None; out=sys.stdout.buffer; last=time.time()
try:
  while True:
    buf=cam.stdout.read(W*H*3)
    if len(buf)<W*H*3: break
    rgb=np.frombuffer(buf,np.uint8).reshape(H,W,3)
    t=time.perf_counter()
    src=(rgb.astype(np.float32)/255).transpose(2,0,1)[None]
    fgr,pha,*rec=s.run(['fgr','pha','r1o','r2o','r3o','r4o'],{'src':src,'r1i':rec[0],'r2i':rec[1],'r3i':rec[2],'r4i':rec[3],'downsample_ratio':ratio})
    al=(pha[0,0]*255).astype(np.uint8)
    times.append(time.perf_counter()-t)
    if first is None: first=time.time()-t0; print(f'first frame {first:.2f}s',file=sys.stderr)
    if a.dump and n in (30,60,90,120):
      import cv2
      bgim=np.full((H,W,3),(255,0,255),np.uint8); bgim[::40]=(0,0,0)
      f=rgb*(al[...,None]/255.)+bgim[...,::-1]*(1-al[...,None]/255.)
      cv2.imwrite(f'{a.dump}{n}.png',f.astype(np.uint8)[...,::-1]); cv2.imwrite(f'{a.dump}{n}_alpha.png',al)
    n+=1
    if not a.bench:
      out.write(np.dstack([rgb,al]).tobytes()); out.flush()
    if a.seconds and time.time()-t0>a.seconds: break
finally:
  cam.terminate()
  ts=np.array(times[5:])*1000
  print(f'frames {n} infer ms mean {ts.mean():.1f} p95 {np.percentile(ts,95):.1f} total fps {n/(time.time()-t0):.1f}',file=sys.stderr)
