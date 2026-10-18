"""
PIFF & PUFF – Degu-flykten
==========================
Två degusar, Piff och Puff, har smitit ut i trädgården.
Katten Pixi jagar dem! Hjälp båda att ta sig tillbaka in i buren
(inne i huset) utan att bli uppätna.

Starta:  python degu_flykten.py
"""
import heapq
import math
import os
import random
import platform

# I WSL används annars mjukvarurendering (llvmpipe) som är mycket långsam.
# d3d12 låter Mesa rita med det riktiga grafikkortet.
if 'microsoft' in platform.release().lower() and os.path.exists('/usr/lib/wsl/lib'):
    os.environ.setdefault('GALLIUM_DRIVER', 'd3d12')

from ursina import *
from ursina.shaders import basic_lighting_shader, unlit_shader

app = Ursina(title='Piff & Puff – Degu-flykten', borderless=False)
window.color = color.rgb32(135, 190, 235)
# (lit_with_shadows_shader kraschar på vissa grafikdrivrutiner, t.ex. i WSL)
Entity.default_shader = basic_lighting_shader
for _counter in (window.fps_counter, window.entity_counter, window.collider_counter):
    _counter.enabled = False


def C(r, g, b, a=1.0):
    return Color(r, g, b, a)


# ---------------------------------------------------------------------------
# Världen: listor med hinder (rektanglar i x/z-planet: x0, x1, z0, z1)
# ---------------------------------------------------------------------------
WORLD = 30                       # världen går från -30 till 30
WALLS = []                       # stoppar alla (väggar, träd, möbler)
CAT_ONLY = []                    # stoppar bara katten (buren, under sängen/soffan)
VISION = []                      # skymmer Pixis sikt (väggar och trädstammar)
FADE = []                        # (box, entity) – blir genomskinliga när de skymmer kameran
BUSHES = []                      # (x, z, radie, entity) – gömställen
HIDE_RECTS = []                  # gömställen under möbler
SEEDS = []                       # solrosfrön

WALL_H = 1.6
WALL_T = 0.3


def box_entity(x0, x1, z0, z1, h, col, y0=0.0, texture=None, solid=True,
               vision=False, fade=False):
    e = Entity(model='cube', color=col, texture=texture,
               position=((x0 + x1) / 2, y0 + h / 2, (z0 + z1) / 2),
               scale=(x1 - x0, h, z1 - z0))
    if texture:
        e.texture_scale = (max(x1 - x0, z1 - z0) / 1.5, h / 1.5)
    b = (x0, x1, z0, z1)
    if solid:
        WALLS.append(b)
    if vision:
        VISION.append(b)
    if fade:
        FADE.append([b, e, False])
    return e


def wall(x0, z0, x1, z1, gaps=(), col=C(.93, .87, .78), texture=None, h=WALL_H):
    """Rak vägg längs x- eller z-axeln, med öppningar (dörrar) i `gaps`."""
    t = WALL_T / 2
    if z0 == z1:
        a, b = x0 - t, x1 + t
    else:
        a, b = z0 - t, z1 + t
    parts, cur = [], a
    for g0, g1 in sorted(gaps):
        if g0 > cur:
            parts.append((cur, g0))
        cur = g1
    if cur < b:
        parts.append((cur, b))
    for p0, p1 in parts:
        if z0 == z1:
            box_entity(p0, p1, z0 - t, z0 + t, h, col, texture=texture, vision=True, fade=True)
        else:
            box_entity(x0 - t, x0 + t, p0, p1, h, col, texture=texture, vision=True, fade=True)


# --- Mark och himmel --------------------------------------------------------
Sky()
Entity(model='plane', scale=(WORLD * 2 + 20, 1, WORLD * 2 + 20), color=C(.45, .75, .35),
       texture='grass', texture_scale=(30, 30))

# Staket runt trädgården
FENCE = C(.62, .45, .28)
for (x0, x1, z0, z1) in [(-WORLD - .3, WORLD + .3, -WORLD - .3, -WORLD),
                         (-WORLD - .3, WORLD + .3, WORLD, WORLD + .3),
                         (-WORLD - .3, -WORLD, -WORLD, WORLD),
                         (WORLD, WORLD + .3, -WORLD, WORLD)]:
    box_entity(x0, x1, z0, z1, 1.0, FENCE, vision=True)

# --- Huset -------------------------------------------------------------------
HX0, HX1, HZ0, HZ1 = -28, -6, 2, 26
Entity(model='plane', position=(-22.5, .02, 14), scale=(11, 1, 24), color=C(.80, .66, .48))   # sovrum
Entity(model='plane', position=(-11.5, .02, 14), scale=(11, 1, 24), color=C(.72, .55, .38))   # vardagsrum
Entity(model='plane', position=(-11.5, .03, 15), scale=(5, 1, 4), color=C(.75, .25, .25))     # matta

BRICK = C(.85, .55, .45)
wall(HX0, HZ0, HX1, HZ0, gaps=[(-12.5, -9.5)], col=BRICK, texture='brick')   # södra väggen + ytterdörr
wall(HX0, HZ1, HX1, HZ1, col=BRICK, texture='brick')                           # norra väggen
wall(HX0, HZ0, HX0, HZ1, col=BRICK, texture='brick')                           # västra väggen
wall(HX1, HZ0, HX1, HZ1, gaps=[(12, 15)], col=BRICK, texture='brick')         # östra väggen + altandörr
wall(-17, HZ0, -17, HZ1, gaps=[(7, 10), (18.5, 21)])                           # innervägg

# Trappsteg / dörrmattor
Entity(model='cube', position=(-11, .05, .9), scale=(3, .1, 1.4), color=C(.5, .4, .3))
Entity(model='cube', position=(-4.9, .05, 13.5), scale=(1.4, .1, 3), color=C(.5, .4, .3))

# --- Buren (målet!) --------------------------------------------------------
CAGE = (-26.8, -22.2, 21.0, 25.6)          # x0, x1, z0, z1
CAGE_DOOR = (22.4, 24.4)                     # öppning på östra sidan (z-led)
cx0, cx1, cz0, cz1 = CAGE
Entity(model='cube', position=((cx0 + cx1) / 2, .05, (cz0 + cz1) / 2),
       scale=(cx1 - cx0, .1, cz1 - cz0), color=C(.95, .85, .5))          # strö i botten
CAGE_H = 1.1
BAR = C(.75, .75, .8)
ct = .05
for b in [(cx0 - ct, cx0 + ct, cz0, cz1), (cx0, cx1, cz1 - ct, cz1 + ct), (cx0, cx1, cz0 - ct, cz0 + ct),
          (cx1 - ct, cx1 + ct, cz0, CAGE_DOOR[0]), (cx1 - ct, cx1 + ct, CAGE_DOOR[1], cz1)]:
    WALLS.append(b)
CAT_ONLY.append(CAGE)


def bars_along(p0, p1, fixed, axis):
    n = int(abs(p1 - p0) / .25)
    for i in range(n + 1):
        p = p0 + (p1 - p0) * i / n
        pos = (fixed, CAGE_H / 2, p) if axis == 'z' else (p, CAGE_H / 2, fixed)
        Entity(model='cube', position=pos, scale=(.04, CAGE_H, .04), color=BAR)
    mid = (p0 + p1) / 2
    ln = abs(p1 - p0)
    for y in (CAGE_H, .12):
        pos = (fixed, y, mid) if axis == 'z' else (mid, y, fixed)
        sc = (.06, .06, ln) if axis == 'z' else (ln, .06, .06)
        Entity(model='cube', position=pos, scale=sc, color=BAR)


bars_along(cz0, cz1, cx0, 'z')
bars_along(cx0, cx1, cz1, 'x')
bars_along(cx0, cx1, cz0, 'x')
bars_along(cz0, CAGE_DOOR[0], cx1, 'z')
bars_along(CAGE_DOOR[1], cz1, cx1, 'z')
Entity(model='cube', position=(cx0 + .8, .35, cz1 - .7), scale=(1, .6, .8), color=C(.6, .4, .2))      # trähus
Entity(model='cube', position=(cx0 + .8, .7, cz1 - .7), scale=(1.1, .1, .9), color=C(.5, .3, .15))
Entity(model='sphere', position=(cx0 + 2.6, .1, cz0 + .8), scale=(.8, .2, .8), color=C(.85, .8, .7))  # sandbad
Entity(model='sphere', position=(cx0 + .5, .35, cz0 + .5), scale=.25, color=C(.2, .7, .3))           # mat
# Grön ljuspelare så att man hittar buren
beacon = Entity(model=Cylinder(16), position=((cx0 + cx1) / 2, 0, (cz0 + cz1) / 2),
                scale=(1.2, 12, 1.2), color=C(.3, 1, .4, .25), shader=unlit_shader)

Text('BUREN', parent=scene, position=((cx0 + cx1) / 2, 2.4, (cz0 + cz1) / 2),
     scale=14, billboard=True, origin=(0, 0), color=color.lime)

# --- Möbler -------------------------------------------------------------------
# Säng (sovrum) – degusar kan gömma sig under, Pixi får inte plats
BED = (-27.8, -24.0, 3.0, 7.0)
bx0, bx1, bz0, bz1 = BED
for (lx, lz) in [(bx0 + .15, bz0 + .15), (bx1 - .15, bz0 + .15), (bx0 + .15, bz1 - .15), (bx1 - .15, bz1 - .15)]:
    Entity(model='cube', position=(lx, .3, lz), scale=(.15, .6, .15), color=C(.4, .25, .15))
Entity(model='cube', position=((bx0 + bx1) / 2, .75, (bz0 + bz1) / 2), scale=(bx1 - bx0, .3, bz1 - bz0), color=C(.4, .25, .15))
Entity(model='cube', position=((bx0 + bx1) / 2, .95, (bz0 + bz1) / 2), scale=(bx1 - bx0 - .1, .15, bz1 - bz0 - .1), color=C(.4, .55, .85))
Entity(model='cube', position=(bx0 + .7, 1.1, (bz0 + bz1) / 2), scale=(.8, .15, 1.6), color=color.white)
CAT_ONLY.append(BED)
HIDE_RECTS.append(BED)

# Garderob
box_entity(-21, -17.4, 2.2, 3.3, 1.4, C(.55, .35, .2), fade=True)

# Soffa (vardagsrum) – också ett gömställe
SOFA = (-13.0, -8.5, 23.2, 25.6)
sx0, sx1, sz0, sz1 = SOFA
SOFA_COL = C(.25, .45, .35)
for (lx, lz) in [(sx0 + .15, sz0 + .15), (sx1 - .15, sz0 + .15), (sx0 + .15, sz1 - .15), (sx1 - .15, sz1 - .15)]:
    Entity(model='cube', position=(lx, .3, lz), scale=(.15, .6, .15), color=C(.2, .15, .1))
Entity(model='cube', position=((sx0 + sx1) / 2, .75, (sz0 + sz1) / 2), scale=(sx1 - sx0, .3, sz1 - sz0), color=SOFA_COL)
Entity(model='cube', position=((sx0 + sx1) / 2, 1.2, sz1 - .2), scale=(sx1 - sx0, .7, .4), color=SOFA_COL)
CAT_ONLY.append(SOFA)
HIDE_RECTS.append(SOFA)

# Bord med fyra ben
tx0, tx1, tz0, tz1 = -13.5, -10.5, 14.0, 16.0
for (lx, lz) in [(tx0, tz0), (tx1 - .2, tz0), (tx0, tz1 - .2), (tx1 - .2, tz1 - .2)]:
    box_entity(lx, lx + .2, lz, lz + .2, .9, C(.45, .3, .18))
Entity(model='cube', position=((tx0 + tx1) / 2, .95, (tz0 + tz1) / 2), scale=(tx1 - tx0, .1, tz1 - tz0), color=C(.5, .33, .2))

# Kökbänk
box_entity(-16.6, -12, 2.4, 3.4, 1.1, C(.9, .9, .9), fade=True)

# --- Trädgården ---------------------------------------------------------------
TREES = [(5, 15), (15, 24), (24, 6), (-20, -10), (10, -14), (26, -16), (-2, -24),
         (-25, -24), (2, 2), (-12, -16), (20, -26), (-27, -4)]
for (x, z) in TREES:
    box_entity(x - .3, x + .3, z - .3, z + .3, 2.2, C(.45, .3, .15), vision=True)
    Entity(model='sphere', position=(x, 3.0, z), scale=2.8, color=C(.2, .55, .2))
    Entity(model='sphere', position=(x + .6, 2.4, z + .3), scale=1.8, color=C(.25, .6, .22))

BUSH_POS = [(12, 0, 1.4), (-8, -8, 1.4), (20, 16, 1.5), (0, -14, 1.4), (-18, -20, 1.5),
            (24, -4, 1.3), (4, 22, 1.4), (-3, 8, 1.3), (15, -22, 1.4), (-24, -14, 1.3),
            (8, -4, 1.2), (-2, 26, 1.2)]
for (x, z, r) in BUSH_POS:
    e = Entity(model='sphere', position=(x, r * .45, z), scale=(r * 2.2, r * 1.3, r * 2.2),
               color=C(.13, .42, .15))
    BUSHES.append([x, z, r, e, False])

# Damm (blockerar alla)
POND = (13, -8, 2.6)
Entity(model='sphere', position=(POND[0], 0, POND[1]), scale=(POND[2] * 2, .12, POND[2] * 2),
       color=C(.25, .5, .85))
pr = POND[2] * .8
WALLS.append((POND[0] - pr, POND[0] + pr, POND[1] - pr, POND[1] + pr))

# Blommor (bara pynt)
random.seed(3)
for _ in range(70):
    x, z = random.uniform(-29, 29), random.uniform(-29, 29)
    if HX0 - 1 < x < HX1 + 1 and HZ0 - 1 < z < HZ1 + 1:
        continue
    Entity(model='sphere', position=(x, .12, z), scale=.18,
           color=random.choice([color.red, color.yellow, color.magenta, color.white, color.orange]),
           shader=unlit_shader)

# Solrosfrön (ger ny ork)
SEED_POS = [(15, -18), (5, -8), (-4, -2), (-10, -1), (-10.7, 5), (-14, 10), (-20, 9),
            (-21, 18), (10, 10), (25, 10), (-8, -20), (1, 25), (-3, 15), (22, -12)]
for (x, z) in SEED_POS:
    s = Entity(model='sphere', position=(x, .3, z), scale=(.26, .14, .42), color=C(.5, .47, .42))
    Entity(parent=s, model='sphere', scale=(.35, 1.1, .9), color=C(.95, .95, .85))
    Entity(parent=s, model='sphere', y=2.5, scale=(.5, .8, .3), color=color.yellow, shader=unlit_shader)
    SEEDS.append(s)


# ---------------------------------------------------------------------------
# Kollision och vägsökning
# ---------------------------------------------------------------------------
def collide_move(x, z, dx, dz, r, boxes):
    """Flytta (x, z) med (dx, dz) men stanna mot rektanglarna i `boxes`."""
    x += dx
    for (x0, x1, z0, z1) in boxes:
        if x + r > x0 and x - r < x1 and z + r > z0 and z - r < z1:
            if dx > 0:
                x = x0 - r - 1e-4
            elif dx < 0:
                x = x1 + r + 1e-4
    z += dz
    for (x0, x1, z0, z1) in boxes:
        if x + r > x0 and x - r < x1 and z + r > z0 and z - r < z1:
            if dz > 0:
                z = z0 - r - 1e-4
            elif dz < 0:
                z = z1 + r + 1e-4
    return x, z


CELL = .5
N = int(WORLD * 2 / CELL)


def to_cell(x, z):
    return (min(N - 1, max(0, int((x + WORLD) / CELL))),
            min(N - 1, max(0, int((z + WORLD) / CELL))))


def cell_center(i, j):
    return (-WORLD + (i + .5) * CELL, -WORLD + (j + .5) * CELL)


def build_grid(boxes, inflate):
    g = [[False] * N for _ in range(N)]
    for (x0, x1, z0, z1) in boxes:
        i0, j0 = to_cell(x0 - inflate, z0 - inflate)
        i1, j1 = to_cell(x1 + inflate, z1 + inflate)
        for i in range(i0, i1 + 1):
            row = g[i]
            for j in range(j0, j1 + 1):
                row[j] = True
    return g


DEGU_GRID = build_grid(WALLS, .3)
CAT_GRID = build_grid(WALLS + CAT_ONLY, .45)
VISION_GRID = build_grid(VISION, 0)

NEIGH = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1),
         (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]


def nearest_free(grid, i, j):
    if not grid[i][j]:
        return (i, j)
    for rad in range(1, 8):
        for di in range(-rad, rad + 1):
            for dj in range(-rad, rad + 1):
                ni, nj = i + di, j + dj
                if 0 <= ni < N and 0 <= nj < N and not grid[ni][nj]:
                    return (ni, nj)
    return None


def find_path(grid, start, goal):
    """A* på rutnätet. Returnerar en lista med (x, z)-punkter."""
    s = nearest_free(grid, *to_cell(*start))
    g = nearest_free(grid, *to_cell(*goal))
    if s is None or g is None:
        return []
    goal_free = not grid[to_cell(*goal)[0]][to_cell(*goal)[1]]

    def h(c):
        dx, dy = abs(c[0] - g[0]), abs(c[1] - g[1])
        return max(dx, dy) + .414 * min(dx, dy)

    came = {s: None}
    cost = {s: 0}
    heap = [(h(s), 0, s)]
    steps = 0
    while heap and steps < 25000:
        steps += 1
        _, c, cur = heapq.heappop(heap)
        if cur == g:
            break
        if c > cost[cur]:
            continue
        ci, cj = cur
        for di, dj, w in NEIGH:
            ni, nj = ci + di, cj + dj
            if not (0 <= ni < N and 0 <= nj < N) or grid[ni][nj]:
                continue
            if di and dj and (grid[ci + di][cj] or grid[ci][cj + dj]):
                continue
            nc = c + w
            if nc < cost.get((ni, nj), 1e9):
                cost[(ni, nj)] = nc
                came[(ni, nj)] = cur
                heapq.heappush(heap, (nc + h((ni, nj)), nc, (ni, nj)))
    if g not in came:
        return []
    path, cur = [], g
    while cur is not None:
        path.append(cell_center(*cur))
        cur = came[cur]
    path.reverse()
    if goal_free:
        path[-1] = goal
    return path


def clear_line(grid, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    dist = math.hypot(dx, dz)
    n = max(1, int(dist / (CELL * .5)))
    for k in range(n + 1):
        i, j = to_cell(a[0] + dx * k / n, a[1] + dz * k / n)
        if grid[i][j]:
            return False
    return True


def random_free_point(grid):
    while True:
        i, j = random.randrange(N), random.randrange(N)
        if not grid[i][j]:
            return cell_center(i, j)


def seg_hits_box(ax, az, bx, bz, box):
    x0, x1, z0, z1 = box
    t0, t1 = 0.0, .97
    for p, d, lo, hi in ((ax, bx - ax, x0, x1), (az, bz - az, z0, z1)):
        if abs(d) < 1e-9:
            if p < lo or p > hi:
                return False
        else:
            ta, tb = (lo - p) / d, (hi - p) / d
            if ta > tb:
                ta, tb = tb, ta
            t0, t1 = max(t0, ta), min(t1, tb)
            if t0 > t1:
                return False
    return True


def angle_lerp(a, b, t):
    d = (b - a + 180) % 360 - 180
    return a + d * t


class Walker:
    """Gemensamt för allt som springer runt: följer en väg genom rutnätet."""

    def follow_path(self, speed, dt, grid, boxes, radius):
        x, z = self.root.x, self.root.z
        while len(self.path) > 1 and clear_line(grid, (x, z), self.path[1]):
            self.path.pop(0)
        if not self.path:
            return False
        tx, tz = self.path[0]
        dx, dz = tx - x, tz - z
        d = math.hypot(dx, dz)
        if d < .15:
            self.path.pop(0)
            return bool(self.path)
        step = min(d, speed * dt)
        nx, nz = collide_move(x, z, dx / d * step, dz / d * step, radius, boxes)
        self.root.x, self.root.z = nx, nz
        self.face(dx, dz, dt)
        return True

    def face(self, dx, dz, dt, rate=12):
        target = math.degrees(math.atan2(dx, dz))
        self.root.rotation_y = angle_lerp(self.root.rotation_y, target, min(1, dt * rate))

    @property
    def xz(self):
        return (self.root.x, self.root.z)


# ---------------------------------------------------------------------------
# Degusarna
# ---------------------------------------------------------------------------
class Degu(Walker):
    RADIUS = .25

    def __init__(self, name, fur, label_col):
        self.name = name
        self.root = Entity()
        self.body = Entity(parent=self.root)
        b = self.body
        cream = C(.93, .85, .7)
        dark = C(fur.r * .6, fur.g * .6, fur.b * .6)
        Entity(parent=b, model='sphere', y=.2, scale=(.34, .3, .55), color=fur)
        Entity(parent=b, model='sphere', y=.15, z=.02, scale=(.28, .22, .45), color=cream)
        head = Entity(parent=b, y=.28, z=.3)
        Entity(parent=head, model='sphere', scale=(.26, .25, .3), color=fur)
        for s in (-1, 1):
            Entity(parent=head, model='sphere', position=(s * .085, .14, -.02), scale=(.11, .13, .04),
                   rotation_z=s * -20, color=C(.75, .55, .5))
            Entity(parent=head, model='sphere', position=(s * .1, .04, .1), scale=.055, color=color.black)
            Entity(parent=b, model='sphere', position=(s * .1, .04, .2), scale=(.08, .06, .12), color=dark)
            Entity(parent=b, model='sphere', position=(s * .12, .05, -.15), scale=(.09, .07, .14), color=dark)
        Entity(parent=head, model='sphere', position=(0, -.01, .15), scale=.045, color=C(.9, .5, .55))
        self.tail = Entity(parent=b, position=(0, .18, -.25))
        Entity(parent=self.tail, model='cube', z=-.25, rotation_x=-15, scale=(.035, .035, .5), color=dark)
        Entity(parent=self.tail, model='sphere', position=(0, .07, -.5), scale=(.08, .08, .14), color=color.black)
        self.label = Text(name, parent=self.root, y=.85, scale=9, billboard=True, origin=(0, 0),
                          color=label_col)
        self.marker = Entity(parent=self.root, model='sphere', y=1.15, scale=.14, color=color.yellow,
                             shader=unlit_shader)
        self.reset((0, 0))

    def reset(self, pos):
        self.root.position = (pos[0], 0, pos[1])
        self.root.rotation_y = 200
        self.safe = False
        self.hidden = False
        self.path = []
        self.repath = 0
        self.anim = random.random() * 10
        self.moving = False

    def animate(self, dt, speed_factor):
        if self.moving:
            self.anim += dt * 14 * speed_factor
            self.body.y = abs(math.sin(self.anim)) * .06
            self.tail.rotation_y = math.sin(self.anim * .5) * 20
        else:
            self.anim += dt * 2
            self.body.y = 0
            self.tail.rotation_y = math.sin(self.anim) * 8

    def in_cage(self):
        x, z = self.xz
        return cx0 + .1 < x < cx1 - .1 and cz0 + .1 < z < cz1 - .1


# ---------------------------------------------------------------------------
# Katten Pixi
# ---------------------------------------------------------------------------
class Cat(Walker):
    RADIUS = .35

    def __init__(self):
        fur = C(.55, .55, .58)
        white = C(.95, .95, .95)
        self.root = Entity()
        self.body = Entity(parent=self.root)
        b = self.body
        Entity(parent=b, model='sphere', y=.5, scale=(.45, .42, .95), color=fur)
        Entity(parent=b, model='sphere', y=.43, z=.15, scale=(.35, .3, .5), color=white)
        self.head = Entity(parent=b, position=(0, .78, .5))
        h = self.head
        Entity(parent=h, model='sphere', scale=(.42, .38, .38), color=fur)
        Entity(parent=h, model='sphere', position=(0, -.07, .14), scale=(.22, .16, .16), color=white)
        Entity(parent=h, model='sphere', position=(0, -.03, .22), scale=.05, color=C(.95, .5, .6))
        for s in (-1, 1):
            Entity(parent=h, model=Cone(4), position=(s * .12, .14, 0), scale=(.13, .2, .08),
                   rotation_z=s * -15, color=fur)
            Entity(parent=h, model='sphere', position=(s * .09, .05, .16), scale=(.09, .1, .05), color=C(.4, .85, .3))
            Entity(parent=h, model='sphere', position=(s * .09, .05, .185), scale=(.03, .08, .02), color=color.black)
            for wz in (-.02, .02):
                Entity(parent=h, model='cube', position=(s * .17, -.06 + wz, .17), rotation_z=s * wz * 400,
                       scale=(.2, .006, .006), color=color.white)
        self.legs = []
        for (lx, lz) in [(-.13, .3), (.13, .3), (-.13, -.3), (.13, -.3)]:
            leg = Entity(parent=b, position=(lx, .35, lz))
            Entity(parent=leg, model='cube', y=-.17, scale=(.1, .35, .1), color=fur)
            Entity(parent=leg, model='sphere', y=-.34, z=.03, scale=(.12, .07, .14), color=white)
            self.legs.append(leg)
        self.tail = Entity(parent=b, position=(0, .6, -.45))
        Entity(parent=self.tail, model='cube', position=(0, .25, -.15), rotation_x=-30, scale=(.08, .6, .08), color=fur)
        Entity(parent=self.tail, model='sphere', position=(0, .53, -.32), scale=.11, color=C(.35, .35, .38))
        self.label = Text('Pixi', parent=self.root, y=1.45, scale=10, billboard=True, origin=(0, 0),
                          color=color.orange)
        self.zzz = Text('Zzz', parent=self.root, y=1.15, x=.3, scale=12, billboard=True, origin=(0, 0),
                        color=color.white)

    def reset(self, pos):
        self.root.position = (pos[0], 0, pos[1])
        self.root.rotation_y = 0
        self.state = 'sleep'
        self.timer = 4.0
        self.path = []
        self.repath = 0
        self.target = None
        self.last_seen = None
        self.pounce_cd = 0
        self.pounce_dir = (0, 0)
        self.anim = 0
        self.body.y = 0
        self.body.scale_y = 1

    def animate(self, dt, speed):
        self.zzz.enabled = self.state == 'sleep'
        if self.state == 'sleep':
            self.body.scale_y = .55
            self.zzz.y = 1.0 + math.sin(time.time() * 2) * .1
            return
        self.body.scale_y = .85 if self.state == 'rest' else 1
        if speed > .1:
            self.anim += dt * speed * 3
            for k, leg in enumerate(self.legs):
                leg.rotation_x = math.sin(self.anim + (k % 2) * math.pi + (k // 2) * math.pi / 2) * 30
            self.body.y = abs(math.sin(self.anim)) * .04
        else:
            for leg in self.legs:
                leg.rotation_x = 0
            self.body.y = 0
        self.tail.rotation_z = math.sin(time.time() * 3) * 15


# ---------------------------------------------------------------------------
# Spelet
# ---------------------------------------------------------------------------
DIFFICULTY = {1: ('Lätt', 3.6), 2: ('Lagom', 4.5), 3: ('Svår', 5.3)}
WALK, SPRINT = 4.5, 7.6
START_PIFF, START_PUFF, START_PIXI = (22, -25), (23.2, -25.5), (6, 8)

piff = Degu('Piff', C(.62, .45, .28), color.cyan)
puff = Degu('Puff', C(.48, .36, .24), color.pink)
pixi = Cat()
degus = [piff, puff]


class Game:
    state = 'menu'
    active = piff
    stamina = 100.0
    seeds = 0
    yaw = 0.0
    cam_dist = 7.0
    cat_speed = 4.5
    message_timer = 0


game = Game()

# --- UI ----------------------------------------------------------------------
info = Text('', position=window.top_left + Vec2(.03, -.03), scale=1.3)
status = Text('', position=(0, .45), origin=(0, 0), scale=1.8)
popup = Text('', position=(0, .36), origin=(0, 0), scale=1.6, color=color.yellow)
bar_bg = Entity(parent=camera.ui, model='quad', origin=(-.5, 0), position=window.top_left + Vec2(.03, -.2),
                scale=(.35, .025), color=C(0, 0, 0, .5))
bar = Entity(parent=camera.ui, model='quad', origin=(-.5, 0), position=window.top_left + Vec2(.03, -.2),
             scale=(.35, .025), color=color.lime, z=-.01)
ork_label = Text('Ork', position=window.top_left + Vec2(.39, -.188), scale=1)
hint = Text('', position=(0, -.45), origin=(0, 0), scale=1.1, color=C(1, 1, 1, .85))
panel = Entity(parent=camera.ui, model='quad', scale=(1.25, .85), color=C(0, 0, 0, .75), z=.1)
center = Text('', position=(0, 0), origin=(0, 0), scale=1.35, line_height=1.15)

MENU_TEXT = """<yellow>PIFF & PUFF  –  Degu-flykten<default>

Degusarna Piff och Puff har smitit ut i trädgården!
Hjälp dem tillbaka in i <lime>buren<default> (inne i huset)
innan katten <orange>Pixi<default> fångar dem.

WASD / piltangenter  –  spring
Shift  –  spurta (kostar ork)
Mus eller Q / E  –  vrid kameran,   hjul  –  zooma
Tab  –  byt mellan Piff och Puff
Göm dig i buskar, under sängen eller soffan!
Solrosfrön ger ny ork.   Esc  –  paus

Välj svårighet:   <lime>1 = Lätt<default>    <yellow>2 = Lagom<default>    <red>3 = Svår<default>"""


def show_center(text, panel_scale=(1.25, .85)):
    center.text = text
    center.enabled = panel.enabled = True
    panel.scale = panel_scale
    set_hud(game.state in ('play', 'paused'))
    mouse.locked = False


def hide_center():
    center.enabled = panel.enabled = False


def flash(text, seconds=3.0):
    popup.text = text
    game.message_timer = seconds


def show_menu():
    game.state = 'menu'
    show_center(MENU_TEXT)


def start_game(level):
    name, game.cat_speed = DIFFICULTY[level]
    piff.reset(START_PIFF)
    puff.reset(START_PUFF)
    pixi.reset(START_PIXI)
    for s in SEEDS:
        s.enabled = True
    game.active = piff
    game.stamina = 100
    game.seeds = 0
    game.yaw = -45
    game.state = 'play'
    hide_center()
    set_hud(True)
    mouse.locked = True
    flash(f'Svårighet: {name}.  Spring till buren – följ det gröna ljuset!', 4)
    camera.position = (START_PIFF[0] + 3, 6, START_PIFF[1] + 7)


def switch_degu():
    other = puff if game.active is piff else piff
    if not other.safe:
        game.active = other
        other.path = []


def end_game(won, who=None):
    game.state = 'won' if won else 'lost'
    if won:
        show_center(f"""<lime>HURRA!<default>

Piff och Puff är tillbaka i buren!
Pixi får nöja sig med kattmat idag.

Solrosfrön: {game.seeds} / {len(SEEDS)}

Tryck <yellow>R<default> för att spela igen""", (1.0, .6))
    else:
        show_center(f"""<red>NEEEJ!<default>

Pixi fångade {who.name}...

Tryck <yellow>R<default> för att försöka igen""", (1.0, .5))


def input(key):
    if game.state == 'menu' and key in ('1', '2', '3'):
        start_game(int(key))
    elif game.state in ('won', 'lost') and key == 'r':
        show_menu()
    elif game.state == 'play':
        if key == 'tab':
            switch_degu()
        elif key == 'escape':
            game.state = 'paused'
            show_center('PAUS\n\nEsc – fortsätt\nM – tillbaka till menyn', (.7, .4))
        elif key == 'scroll up':
            game.cam_dist = max(3.5, game.cam_dist - .7)
        elif key == 'scroll down':
            game.cam_dist = min(16, game.cam_dist + .7)
    elif game.state == 'paused':
        if key == 'escape':
            game.state = 'play'
            hide_center()
            mouse.locked = True
        elif key == 'm':
            show_menu()


# --- Spelarlogik ---------------------------------------------------------------
def update_player(dt):
    d = game.active
    ix = (held_keys['d'] or held_keys['right arrow']) - (held_keys['a'] or held_keys['left arrow'])
    iz = (held_keys['w'] or held_keys['up arrow']) - (held_keys['s'] or held_keys['down arrow'])
    yaw = math.radians(game.yaw)
    fx, fz = math.sin(yaw), math.cos(yaw)
    rx, rz = math.cos(yaw), -math.sin(yaw)
    mx, mz = fx * iz + rx * ix, fz * iz + rz * ix
    length = math.hypot(mx, mz)
    d.moving = length > 0
    sprinting = d.moving and held_keys['shift'] and game.stamina > 0
    if sprinting:
        game.stamina = max(0, game.stamina - 28 * dt)
    else:
        game.stamina = min(100, game.stamina + 14 * dt)
    if d.moving:
        speed = SPRINT if sprinting else WALK
        mx, mz = mx / length * speed * dt, mz / length * speed * dt
        d.root.x, d.root.z = collide_move(d.root.x, d.root.z, mx, mz, Degu.RADIUS, WALLS)
        d.face(mx, mz, dt, 15)
    d.animate(dt, 1.6 if sprinting else 1)


def update_follower(dt):
    d = puff if game.active is piff else piff
    if d.safe:
        d.moving = False
        d.animate(dt, 1)
        return
    lead = game.active
    dist = math.dist(d.xz, lead.xz)
    d.moving = False
    if dist > 1.4:
        d.repath -= dt
        if d.repath <= 0 or not d.path:
            d.repath = .3
            d.path = find_path(DEGU_GRID, d.xz, lead.xz)
        speed = SPRINT + .3 if dist > 3.5 else WALK
        d.moving = d.follow_path(speed, dt, DEGU_GRID, WALLS, Degu.RADIUS)
    d.animate(dt, 1.6 if dist > 3.5 else 1)


def is_hidden(d):
    x, z = d.xz
    for (bx, bz, r, *_ ) in BUSHES:
        if (x - bx) ** 2 + (z - bz) ** 2 < (r * .85) ** 2:
            return True
    for (x0, x1, z0, z1) in HIDE_RECTS:
        if x0 < x < x1 and z0 < z < z1:
            return True
    return False


def cat_sees(d):
    if d.safe or d.hidden:
        return False
    dist = math.dist(pixi.xz, d.xz)
    if dist < 2.5:
        return True
    return dist < 22 and clear_line(VISION_GRID, pixi.xz, d.xz)


def update_cat(dt):
    c = pixi
    visible = [d for d in degus if cat_sees(d)]
    nearest = min(visible, key=lambda d: math.dist(c.xz, d.xz)) if visible else None
    c.pounce_cd -= dt
    speed = 0

    if c.state == 'sleep':
        c.timer -= dt
        close = any(math.dist(c.xz, d.xz) < 5 for d in degus if not d.safe)
        if c.timer <= 0 or close:
            c.state = 'wander'
            c.path = []
            flash('Pixi vaknade! Mjaaau!', 2.5)

    elif c.state in ('wander', 'search'):
        if nearest:
            c.state = 'chase'
            c.target = nearest
            flash(f'Pixi har sett {nearest.name}! SPRING!', 2)
        elif c.path:
            speed = 3.6 if c.state == 'search' else 2.4
            if not c.follow_path(speed, dt, CAT_GRID, WALLS + CAT_ONLY, Cat.RADIUS):
                c.path = []
        else:
            c.timer -= dt
            c.root.rotation_y += dt * 60
            if c.timer <= 0:
                c.state = 'wander'
                c.timer = random.uniform(1, 2.5)
                targets = [d for d in degus if not d.safe]
                if targets and random.random() < .45:
                    # Pixi "nosar" sig fram mot ungefär rätt håll
                    t = random.choice(targets)
                    goal = (t.root.x + random.uniform(-7, 7), t.root.z + random.uniform(-7, 7))
                else:
                    goal = random_free_point(CAT_GRID)
                c.path = find_path(CAT_GRID, c.xz, goal)

    elif c.state == 'chase':
        if c.target not in visible:
            c.target = nearest
        if c.target is None:
            c.state = 'search'
            c.timer = 2.5
            c.path = find_path(CAT_GRID, c.xz, c.last_seen) if c.last_seen else []
        else:
            c.last_seen = c.target.xz
            dist = math.dist(c.xz, c.target.xz)
            if dist < 3.2 and c.pounce_cd <= 0:
                dx, dz = c.target.root.x - c.root.x, c.target.root.z - c.root.z
                ln = math.hypot(dx, dz) or 1
                c.pounce_dir = (dx / ln, dz / ln)
                c.state = 'pounce'
                c.timer = .45
                c.pounce_cd = 3.2
            else:
                c.repath -= dt
                if c.repath <= 0 or not c.path:
                    c.repath = .25
                    c.path = find_path(CAT_GRID, c.xz, c.target.xz)
                speed = game.cat_speed
                c.follow_path(speed, dt, CAT_GRID, WALLS + CAT_ONLY, Cat.RADIUS)

    elif c.state == 'pounce':
        speed = 10
        dx, dz = c.pounce_dir
        c.root.x, c.root.z = collide_move(c.root.x, c.root.z, dx * speed * dt, dz * speed * dt,
                                          Cat.RADIUS, WALLS + CAT_ONLY)
        c.face(dx, dz, dt, 20)
        c.body.y = math.sin((.45 - c.timer) / .45 * math.pi) * .4
        c.timer -= dt
        if c.timer <= 0:
            c.state = 'rest'
            c.timer = 1.1

    elif c.state == 'rest':
        c.timer -= dt
        if c.timer <= 0:
            c.state = 'chase' if nearest else 'search'
            c.target = nearest
            c.path = []
            c.timer = 2.5

    if c.state != 'pounce':
        c.animate(dt, speed)

    if c.state not in ('sleep', 'rest'):
        for d in degus:
            if not d.safe and math.dist(c.xz, d.xz) < .75:
                end_game(False, d)
                return


def look_toward(t):
    d = t - camera.position
    camera.rotation = (math.degrees(math.atan2(-d.y, math.hypot(d.x, d.z))),
                       math.degrees(math.atan2(d.x, d.z)), 0)


def set_hud(on):
    for e in (info, status, bar, bar_bg, ork_label, hint):
        e.enabled = on


def update_camera(dt):
    if mouse.locked:
        game.yaw += mouse.velocity[0] * 140
    game.yaw += (held_keys['e'] - held_keys['q']) * 110 * dt
    t = game.active.root.position + Vec3(0, .4, 0)
    yaw = math.radians(game.yaw)
    dist = game.cam_dist
    desired = t + Vec3(-math.sin(yaw) * dist, dist * .7, -math.cos(yaw) * dist)
    camera.position = lerp(camera.position, desired, min(1, dt * 7))
    look_toward(t)

    # Gör väggar genomskinliga om de skymmer degusen
    cx, cz = camera.x, camera.z
    px, pz = game.active.xz
    for item in FADE:
        hit = seg_hits_box(cx, cz, px, pz, item[0])
        if hit != item[2]:
            item[2] = hit
            item[1].alpha = .25 if hit else 1
    for b in BUSHES:
        near = math.dist((b[0], b[1]), (px, pz)) < b[2] + .4
        if near != b[4]:
            b[4] = near
            b[3].alpha = .4 if near else 1


def update_ui():
    a = game.active
    other = puff if a is piff else piff
    safe_count = sum(d.safe for d in degus)
    info.text = (f'Du styr: <yellow>{a.name}<default>   (Tab byter)\n'
                 f'I buren: {safe_count} / 2\n'
                 f'Solrosfrön: {game.seeds}')
    bar.scale_x = .35 * game.stamina / 100
    bar.color = color.lime if game.stamina > 30 else color.orange
    texts = {
        'sleep': ('Pixi sover... smyg förbi!', color.white),
        'wander': ('Pixi strövar omkring', color.white),
        'search': ('Pixi letar efter er...', color.yellow),
        'chase': ('PIXI JAGAR ER!', color.red),
        'pounce': ('PIXI HOPPAR!', color.red),
        'rest': ('Pixi pustar ut – spring!', color.orange),
    }
    status.text, status.color = texts.get(pixi.state, ('', color.white))
    tips = []
    if a.hidden:
        tips.append('Du är gömd!')
    if not other.safe and math.dist(a.xz, other.xz) > 12:
        tips.append(f'{other.name} är långt bort – tryck Tab för att hämta')
    hint.text = '   ·   '.join(tips)
    for d in degus:
        d.marker.enabled = d is a
        d.marker.y = 1.15 + math.sin(time.time() * 4) * .07


def update():
    dt = min(time.dt, .05)
    if game.message_timer > 0:
        game.message_timer -= dt
        popup.enabled = game.message_timer > 0
    if game.state != 'play':
        return
    update_player(dt)
    update_follower(dt)
    for d in degus:
        d.hidden = is_hidden(d)

    # Frön
    for s in SEEDS:
        s.rotation_y += 90 * dt
        if s.enabled and any(math.dist((s.x, s.z), d.xz) < .6 for d in degus):
            s.enabled = False
            game.seeds += 1
            game.stamina = min(100, game.stamina + 45)

    # Kommit in i buren?
    for d in degus:
        if not d.safe and d.in_cage():
            d.safe = True
            d.moving = False
            d.path = []
            other = puff if d is piff else piff
            if other.safe:
                end_game(True)
                return
            flash(f'{d.name} är i säkerhet! Nu ska {other.name} hem.', 3.5)
            if d is game.active:
                game.active = other

    update_cat(dt)
    update_camera(dt)
    update_ui()


camera.fov = 75

piff.reset(START_PIFF)
puff.reset(START_PUFF)
pixi.reset(START_PIXI)
camera.position = (-5, 30, -35)
look_toward(Vec3(-5, 0, 5))
show_menu()

if os.environ.get('DEGU_TEST'):
    # Testläge: kör ett scenario, ta skärmdumpar och avsluta
    from panda3d.core import Filename
    out = os.environ['DEGU_TEST']

    def _shot(name):
        base.win.saveScreenshot(Filename(out + name))

    def _step(t, f):
        invoke(f, delay=t)

    def _follow_setup():
        piff.root.position = (-21, 0, 18)
        puff.root.position = (-11, 0, -3)
        pixi.root.position = (25, 0, 25)
        pixi.timer = 999
        game.yaw = -40

    def _follow_check():
        print('TEST follow: puff->piff dist', round(math.dist(puff.xz, piff.xz), 2))

    def _cage():
        piff.root.position = (-24.5, 0, 23.4)

    def _cage_check():
        print('TEST cage: piff.safe', piff.safe, 'active', game.active.name)

    def _cat():
        pixi.state = 'wander'
        pixi.path = []
        pixi.root.position = (-12, 0, 12)
        puff.root.position = (-10, 0, 8)

    def _cat_check():
        print('TEST cat: state', game.state, 'pixi', pixi.state)

    _step(1.5, lambda: _shot('_menu.png'))
    _step(2, lambda: start_game(2))
    _step(3.5, lambda: _shot('_play.png'))
    _step(4, _follow_setup)
    for _k in range(10):
        _step(4.5 + _k * .5, lambda: print('TEST fps', round(1 / max(time.dt, 1e-4)), [round(v, 1) for v in puff.xz]))
    _step(9, _follow_check)
    _step(9.1, lambda: _shot('_house.png'))
    _step(9.5, _cage)
    _step(10, _cage_check)
    _step(10.5, _cat)
    _step(14, _cat_check)
    _step(14.2, lambda: _shot('_end.png'))
    _step(14.5, application.quit)

app.run()
