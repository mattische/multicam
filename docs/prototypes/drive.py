import pty,os,sys,time,json,subprocess,select
def geo():
    o=subprocess.run(['hyprctl','clients','-j'],capture_output=True,text=True).stdout
    return {c['class']:(c['at'][0],c['at'][1],c['size'][0],c['size'][1]) for c in json.loads(o) if c['class'].startswith('Multicam')}
def act():
    return json.loads(subprocess.run(['hyprctl','activewindow','-j'],capture_output=True,text=True).stdout or '{}').get('class')
def start(env_extra={}):
    pid,fd=pty.fork()
    if pid==0:
        os.environ.update(env_extra); os.execv('./kbd-proto.sh',['kbd-proto.sh'])
    return pid,fd
def drain(fd,t=0.1):
    out=b''
    while select.select([fd],[],[],t)[0]:
        try: d=os.read(fd,65536)
        except OSError: break
        if not d: break
        out+=d
    return out
