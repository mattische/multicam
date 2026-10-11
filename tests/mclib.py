"""Gemensamt testbibliotek för multicam: pty-drivning, hyprctl-hjälpare, städkontroller."""
import os, pty, sys, time, json, subprocess, select, re, shutil, fcntl, termios, struct, signal

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(REPO, 'bin', 'multicam')
SCRATCH = '/tmp/claude-1000/multicam-tests'
ANSI = re.compile(r'\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[()][A-Z0-9]|\x1b[=>]')


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, **kw)


def hypr_env():
    env = dict(os.environ)
    env.setdefault('XDG_RUNTIME_DIR', '/run/user/1000')
    env.setdefault('WAYLAND_DISPLAY', 'wayland-1')
    if 'HYPRLAND_INSTANCE_SIGNATURE' not in env:
        d = '/run/user/1000/hypr'
        env['HYPRLAND_INSTANCE_SIGNATURE'] = sorted(os.listdir(d), key=lambda n: os.path.getmtime(os.path.join(d, n)))[-1]
    return env


os.environ.update(hypr_env())


def clients():
    return json.loads(sh('hyprctl clients -j').stdout)


def mc_clients():
    return {c['class']: c for c in clients() if re.match(r'^Multicam[AB]$', c['class'])}


def geo():
    return {k: (c['at'][0], c['at'][1], c['size'][0], c['size'][1]) for k, c in mc_clients().items()}


def active_class():
    try:
        return json.loads(sh('hyprctl activewindow -j').stdout or '{}').get('class')
    except Exception:
        return None


def active_addr():
    try:
        return json.loads(sh('hyprctl activewindow -j').stdout or '{}').get('address')
    except Exception:
        return None


def monitors():
    return json.loads(sh('hyprctl monitors -j').stdout)


def default_source():
    return sh('pactl get-default-source').stdout.strip()


def own_mpv_for_multicam():
    """mpv-processer med wayland-app-id=Multicam* samt bg.py (bara multicams egna)."""
    out = []
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        try:
            comm = open(f'/proc/{pid}/comm').read().strip()
            cmd = open(f'/proc/{pid}/cmdline').read().replace('\0', ' ')
        except OSError:
            continue
        if (comm == 'mpv' and 'wayland-app-id=Multicam' in cmd) or (comm.startswith('python') and 'lib/bg.py' in cmd):
            out.append(f'{pid} {cmd[:80]}')
    return out


def rules_enabled():
    """hyprctl har inget `rules -j`; sonden är ett eget foot-fönster med klass MulticamA:
    är multicams regel aktiv blir det flytande + fastnålat (float=true, pin=true). Returnerar lista (tom = inga regler aktiva)."""
    p = subprocess.Popen(['foot', '--app-id=MulticamA', '-e', 'sleep', '30'], env=hypr_env(),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        c = None
        end = time.time() + 5
        while time.time() < end and not c:
            c = [x for x in clients() if x['class'] == 'MulticamA' and x['pid'] == p.pid]
            time.sleep(0.1)
        if not c:
            return None
        time.sleep(0.2)
        c = [x for x in clients() if x['class'] == 'MulticamA' and x['pid'] == p.pid][0]
        return [f'regel aktiv (floating={c["floating"]} pinned={c["pinned"]})'] if (c['floating'] or c['pinned']) else []
    finally:
        p.terminate()
        try:
            p.wait(3)
        except Exception:
            p.kill()


def gsr_pids():
    return sh("pgrep -f '^gpu-screen-recorder'").stdout.split()


def make_home(name, config=None):
    home = os.path.join(SCRATCH, 'home-' + name)
    shutil.rmtree(home, ignore_errors=True)
    os.makedirs(os.path.join(home, '.config', 'multicam'))
    if config:
        with open(os.path.join(home, '.config', 'multicam', 'config'), 'w') as f:
            f.write(config)
    return home


def out_dir(name):
    d = os.path.join(SCRATCH, 'out-' + name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    return d


class Session:
    """Kör multicam i en pty (utan terminalfönster)."""

    def __init__(self, home, outdir=None, env=None, cols=100, rows=34, args=()):
        e = hypr_env()
        e['HOME'] = home
        e['TERM'] = 'xterm-256color'
        e['MULTICAM_LOG'] = os.path.join(home, 'multicam.log')
        e.pop('MULTICAM_OUTPUT_DIR', None)
        if outdir:
            e['MULTICAM_OUTPUT_DIR'] = outdir
        if env:
            e.update(env)
        self.home = home
        self.buf = ''
        pid, fd = pty.fork()
        if pid == 0:
            os.execve(BIN, [BIN, *args], e)
        self.pid, self.fd = pid, fd
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
        self.exit_status = None

    def pump(self, t=0.1):
        end = time.time() + t
        while True:
            r = select.select([self.fd], [], [], max(0, end - time.time()))[0]
            if not r:
                break
            try:
                d = os.read(self.fd, 65536)
            except OSError:
                break
            if not d:
                break
            self.buf += d.decode('utf-8', 'replace')
        return self.buf

    def screen(self):
        """Senast ritade ramen som text (utan ANSI)."""
        self.pump(0.05)
        last = self.buf.rsplit('\x1b[H', 1)[-1]
        return ANSI.sub('', last)

    def send(self, keys, settle=0.25):
        if isinstance(keys, str):
            keys = keys.encode()
        os.write(self.fd, keys)
        self.pump(settle)

    def wait_for(self, text, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            if text in self.screen():
                return True
            self.pump(0.1)
        return False

    def alive(self):
        if self.exit_status is not None:
            return False
        try:
            p, st = os.waitpid(self.pid, os.WNOHANG)
        except ChildProcessError:
            return False
        if p:
            self.exit_status = st
            return False
        return True

    def wait_exit(self, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            self.pump(0.1)
            if not self.alive():
                return True
        return False

    def kill(self, sig=signal.SIGTERM):
        try:
            os.kill(self.pid, sig)
        except ProcessLookupError:
            pass

    def close(self):
        if self.alive():
            self.kill(signal.SIGTERM)
            if not self.wait_exit(8):
                self.kill(signal.SIGKILL)
                self.wait_exit(2)
        try:
            os.close(self.fd)
        except OSError:
            pass


UP, DOWN, RIGHT, LEFT = '\x1b[A', '\x1b[B', '\x1b[C', '\x1b[D'
SUP, SDOWN, SRIGHT, SLEFT = '\x1b[1;2A', '\x1b[1;2B', '\x1b[1;2C', '\x1b[1;2D'
PGUP, PGDN, F5, ESC, ENTER, TAB = '\x1b[5~', '\x1b[6~', '\x1b[15~', '\x1b', '\r', '\t'

CAMS = {'C920': '/dev/video2', 'FaceTime': '/dev/video0'}

BASE_CFG = """CAM_A_DEV=/dev/video2
CAM_A_NAME=HD Pro Webcam C920
CAM_A_SHAPE={shape}
CAM_A_RING={ring}
CAM_A_COLOR={color}
CAM_A_THICK={thick}
CAM_A_BG=off
CAM_A_SIZE={size}
CAM_B_DEV=
CAM_B_NAME=
MIC=
DESKTOP_AUDIO=off
SCREEN=
"""


def cfg(shape='rect', ring='off', color='#ff3399', thick=4, size=240, extra=''):
    return BASE_CFG.format(shape=shape, ring=ring, color=color, thick=thick, size=size) + extra


def wait_until(fn, timeout=10, step=0.1):
    end = time.time() + timeout
    while time.time() < end:
        v = fn()
        if v:
            return v
        time.sleep(step)
    return None


def start_to_preview(sess, timeout=15):
    """Formulär -> F5 -> vänta på förhandsvisning och mappade kamerafönster."""
    assert sess.wait_for('multicam', 5), 'formuläret visades inte'
    sess.send(F5)
    assert sess.wait_for('FÖRHANDSVISNING', timeout), 'ingen förhandsvisning:\n' + sess.screen()
    return True


def wake():
    """Skärmarna kan vara släckta (DPMS) efter inaktivitet; då levereras inga bildrutor."""
    sh("hyprctl dispatch 'hl.dsp.dpms({ action = \"on\" })'")
    time.sleep(0.3)


def grim(path, geometry=None, output=None):
    cmd = ['grim']
    if geometry:
        cmd += ['-g', geometry]
    if output:
        cmd += ['-o', output]
    cmd.append(path)
    try:
        return subprocess.run(cmd, capture_output=True, env=hypr_env(), timeout=15).returncode == 0
    except subprocess.TimeoutExpired:
        return False


class Report:
    def __init__(self):
        self.rows = []

    def add(self, tid, status, evidence):
        self.rows.append((tid, status, evidence))
        print(f'{tid}: {status}  {evidence}', flush=True)
