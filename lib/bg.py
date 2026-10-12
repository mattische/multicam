#!/usr/bin/env python3
"""multicam background removal: camera -> RVM (ONNX) -> RGBA rawvideo on stdout (for mpv).
Model: Robust Video Matting (GPL-3.0), https://github.com/PeterL1n/RobustVideoMatting"""
import sys, time, subprocess, argparse, signal
import numpy as np
import onnxruntime as ort

p = argparse.ArgumentParser()
p.add_argument('--dev', default='/dev/video0')
p.add_argument('--w', type=int, default=640)
p.add_argument('--h', type=int, default=480)
p.add_argument('--fps', type=int, default=30)
p.add_argument('--ratio', type=float, default=0.25)
p.add_argument('--threads', type=int, default=2)
p.add_argument('--seconds', type=float, default=0)
p.add_argument('--input-format', default='')
p.add_argument('--model', required=True)
p.add_argument('--bench', action='store_true', help='write no video, only measure')
a = p.parse_args()

signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
so = ort.SessionOptions()
so.intra_op_num_threads = a.threads
so.inter_op_num_threads = 1
sess = ort.InferenceSession(a.model, so, providers=['CPUExecutionProvider'])
W, H = a.w, a.h
cmd = ['ffmpeg', '-loglevel', 'error', '-f', 'v4l2']
if a.input_format:
    cmd += ['-input_format', a.input_format]
cmd += ['-video_size', f'{W}x{H}', '-framerate', str(a.fps), '-i', a.dev, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
cam = subprocess.Popen(cmd, stdout=subprocess.PIPE)
rec = [np.zeros((1, 1, 1, 1), np.float32)] * 4
ratio = np.array([a.ratio], np.float32)
n = 0; times = []; t0 = time.time(); out = sys.stdout.buffer
try:
    while True:
        buf = cam.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        rgb = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        t = time.perf_counter()
        src = (rgb.astype(np.float32) / 255).transpose(2, 0, 1)[None]
        fgr, pha, *rec = sess.run(['fgr', 'pha', 'r1o', 'r2o', 'r3o', 'r4o'],
                                  {'src': src, 'r1i': rec[0], 'r2i': rec[1], 'r3i': rec[2], 'r4i': rec[3],
                                   'downsample_ratio': ratio})
        al = (pha[0, 0] * 255).astype(np.uint8)
        times.append(time.perf_counter() - t)
        n += 1
        if not a.bench:
            out.write(np.dstack([rgb, al]).tobytes())
            out.flush()
        if a.seconds and time.time() - t0 > a.seconds:
            break
except (BrokenPipeError, KeyboardInterrupt):
    pass
finally:
    cam.terminate()
    if times:
        ts = np.array(times[5:] or times) * 1000
        print(f'frames {n} infer ms mean {ts.mean():.1f} p95 {np.percentile(ts, 95):.1f} fps {n / (time.time() - t0):.1f}',
              file=sys.stderr)
