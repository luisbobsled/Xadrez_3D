"""Cenários do Xadrez de Batalha 3D (castelo, campo de batalha, salão do trono), modelados no Blender.
Reaproveita os construtores do build_pieces.py. Coordenadas (x, h, f): f>0 = lado das brancas (câmera), f<0 = fundo.
"""
import sys, math, random
sys.argv = [a for a in sys.argv]
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_HERE, 'build_pieces.py'), encoding='utf-8').read().split('# ===================== PEÃO')[0])
import bmesh, bpy
from mathutils import Vector, Matrix, noise

random.seed(11)
OUT = _os.path.join(_HERE, '..', 'assets', 'scenes.glb')
for k, c in {'stone': (0.55, 0.53, 0.5, 1), 'cobble': (0.45, 0.43, 0.4, 1), 'roof': (0.2, 0.25, 0.4, 1), 'wood': (0.4, 0.27, 0.15, 1),
             'banner': (0.55, 0.07, 0.12, 1), 'banner2': (0.1, 0.2, 0.55, 1), 'flame': (1, 0.6, 0.2, 1), 'ground': (0.3, 0.33, 0.2, 1),
             'rock': (0.42, 0.41, 0.4, 1), 'bark': (0.24, 0.17, 0.12, 1), 'cloth': (0.7, 0.65, 0.55, 1), 'marble': (0.9, 0.88, 0.85, 1),
             'column': (0.85, 0.82, 0.77, 1), 'carpet': (0.5, 0.05, 0.1, 1), 'velvet': (0.4, 0.03, 0.08, 1), 'glass': (0.75, 0.85, 1, 1),
             'gold': (0.85, 0.65, 0.2, 1)}.items():
    COL[k] = c
METAL['gold'] = 0.9


def uv_box(bm, s=0.5):
    bm.normal_update()
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            co = l.vert.co
            l[uv].uv = (co.x * s, co.y * s) if ax == 2 else ((co.x * s, co.z * s) if ax == 1 else (co.y * s, co.z * s))


_old_add = Part.add
def _add(self, bm, m):
    uv_box(bm)
    return _old_add(self, bm, m)
Part.add = _add


def grid(size, n, h=-0.405, height_fn=None):
    bm = bmesh.new()
    vs = []
    for i in range(n + 1):
        row = []
        for j in range(n + 1):
            x = -size / 2 + size * i / n
            f = -size / 2 + size * j / n
            hh = h + (height_fn(x, f) if height_fn else 0)
            row.append(bm.verts.new(P(x, hh, f)))
        vs.append(row)
    for i in range(n):
        for j in range(n):
            bm.faces.new((vs[i][j], vs[i][j + 1], vs[i + 1][j + 1], vs[i + 1][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    return bm


def rock(c, r):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1)
    sd = random.random() * 100
    for v in bm.verts:
        d = 1 + 0.28 * noise.noise(v.co * 1.7 + Vector((sd, 0, 0)))
        v.co *= d
    bmesh.ops.transform(bm, matrix=Matrix.Diagonal((r * random.uniform(0.9, 1.4), r * random.uniform(0.9, 1.3), r * random.uniform(0.5, 0.8), 1)), verts=bm.verts)
    return xf(bm, c, yaw=random.uniform(0, 6.28))


def torch(part, c, yaw, name):
    part.add(box((c[0], c[1], c[2]), (0.08, 0.35, 0.08), bev=0.01, pitch=0.35, yaw=yaw), 'wood')
    part.add(tube((c[0], c[1] + 0.15, c[2]), (c[0], c[1] + 0.25, c[2]), 0.07, 0.09, seg=10), 'iron')
    fl = sphere((c[0], c[1] + 0.38, c[2]), 0.1, (1, 1.8, 1), u=10, v=8)
    part.add(fl, 'flame')
    empty(name, part, (c[0], c[1] + 0.45, c[2]))


def banner(part, c, w, h, yaw, mat='banner', emblem=True):
    bm = bmesh.new()
    nx, nh = 6, 10
    vs = [[bm.verts.new(P(-w / 2 + w * i / nx, -h * j / nh, 0.04 * math.sin(j / nh * 3 + i))) for j in range(nh + 1)] for i in range(nx + 1)]
    for i in range(nx):
        for j in range(nh):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
    tip = bm.verts.new(P(0, -h - w * 0.35, 0.03))
    for i in range(nx):
        bm.faces.new((vs[i][nh], vs[i + 1][nh], tip))
    part.add(xf(bm, c, yaw=yaw), mat)
    part.add(xf(tube((-w / 2 - 0.08, 0, 0), (w / 2 + 0.08, 0, 0), 0.04, seg=8), c, yaw=yaw), 'gold')
    if emblem:
        part.add(xf(sphere((0, -h * 0.45, 0.05), w * 0.2, (1, 1, 0.15), u=16, v=8), c, yaw=yaw), 'gold')


# ===================== CASTELO =====================
def build_castle():
    R = root('scene_castle')
    g = Part('castle_ground', R)
    g.add(grid(90, 6), 'cobble')
    # caminho de terra/pedra ao redor do tabuleiro
    for i in range(28):
        a = i / 28 * 2 * math.pi
        g.add(box((math.cos(a) * 8.2, -0.38, math.sin(a) * 8.2), (1.6, 0.06, 0.9), bev=0.04, yaw=-a), 'stone')
    g.build()
    w = Part('castle_walls', R)
    L, H, T = 15.0, 5.0, 1.4
    for side in range(4):
        yaw = side * math.pi / 2
        for seg in range(-6, 7):
            if side == 0 and abs(seg) <= 1:
                continue  # portão (fundo)
            w.add(xf(box((seg * 2.2, H / 2 - 0.4, -L), (2.25, H, T), bev=0.03), yaw=yaw), 'stone')
            for k in (-0.5, 0.5):
                w.add(xf(box((seg * 2.2 + k * 1.0, H - 0.4 + 0.35, -L + T * 0.35), (0.7, 0.7, 0.45), bev=0.03), yaw=yaw), 'stone')
            w.add(xf(box((seg * 2.2, H - 0.45, -L - 0.05), (2.25, 0.2, T + 0.25), bev=0.03), yaw=yaw), 'stone')
    # portão em arco com grade
    w.add(box((-3.3, H / 2 - 0.4, -L), (2.4, H, T), bev=0.03), 'stone')
    w.add(box((3.3, H / 2 - 0.4, -L), (2.4, H, T), bev=0.03), 'stone')
    w.add(box((0, H - 1.1, -L), (4.4, 1.4, T), bev=0.03), 'stone')
    w.add(ring((0, 2.6, -L + T / 2 + 0.02), 1.6, 0.18, plane='xf', seg=20, tseg=8, a0=0, a1=math.pi), 'stone')
    for x in [-1.8 + 0.36 * i for i in range(11)]:
        w.add(box((x, 1.6, -L + 0.1), (0.07, 3.6, 0.07), bev=0), 'iron')
    for hh in (0.6, 1.6, 2.6):
        w.add(box((0, hh, -L + 0.1), (3.6, 0.07, 0.07), bev=0), 'iron')
    # torres nos cantos
    for sx in (-1, 1):
        for sf in (-1, 1):
            c = (sx * L, 0, sf * L)
            w.add(lathe([(0, -0.4), (2.4, -0.4), (2.4, 0.2), (2.2, 0.4), (2.1, 7.0), (2.45, 7.3), (2.45, 7.9), (0, 7.9)], seg=28, off=c), 'stone')
            for k in range(12):
                a = k / 12 * 2 * math.pi
                w.add(box((c[0] + math.cos(a) * 2.3, 8.15, c[2] + math.sin(a) * 2.3), (0.7, 0.5, 0.4), bev=0.03, yaw=-a + math.pi / 2), 'stone')
            w.add(lathe([(0, 8.3), (2.0, 8.3), (0, 11.6)], seg=20, off=c), 'roof')
            w.add(tube((c[0], 11.5, c[2]), (c[0], 12.6, c[2]), 0.05, seg=6), 'wood')
            for hh in (2.5, 5.0):
                for a in (0.3, 2.0, 3.5, 5.0):
                    w.add(box((c[0] + math.cos(a) * 2.15, hh, c[2] + math.sin(a) * 2.15), (0.25, 0.7, 0.2), bev=0.02, yaw=-a + math.pi / 2), 'iron')
    w.build()
    d = Part('castle_props', R)
    for i, (x, f, yaw) in enumerate([(-6, -L + 0.75, 0), (6, -L + 0.75, 0), (-L + 0.75, -5, math.pi / 2), (L - 0.75, -5, -math.pi / 2),
                                     (-L + 0.75, 5, math.pi / 2), (L - 0.75, 5, -math.pi / 2)]):
        torch(d, (x, 2.4, f), yaw, f'light_torch_{i}')
    for i, (x, f, yaw) in enumerate([(-3.8, -L + 0.72, 0), (3.8, -L + 0.72, 0), (-L + 0.72, 0, math.pi / 2), (L - 0.72, 0, -math.pi / 2)]):
        banner(d, (x, 4.2, f), 1.3, 2.6, yaw, 'banner' if i % 2 == 0 else 'banner2')
    # barris, caixotes e um suporte de armas
    for (x, f) in [(-11, -11), (-10, -12.2), (11.5, -10.5), (11, 9), (-11.5, 10)]:
        d.add(lathe([(0, -0.4), (0.45, -0.4), (0.52, 0.1), (0.45, 0.6), (0, 0.6)], seg=16, off=(x, 0, f)), 'wood')
        for hh in (-0.2, 0.4):
            d.add(ring((x, hh, f), 0.5, 0.03, seg=16, tseg=5), 'iron')
    for (x, f, s) in [(10, -12, 1.0), (10.9, -11.2, 0.7), (-12, 7.5, 0.9)]:
        d.add(box((x, -0.4 + s / 2, f), (s, s, s), bev=0.04, yaw=random.uniform(0, 1)), 'wood')
    d.add(box((-8, 0.3, -L + 1.0), (2.2, 0.1, 0.3), bev=0.02), 'wood')
    for k in range(5):
        d.add(tube((-8.8 + k * 0.4, -0.4, -L + 1.0), (-8.8 + k * 0.4, 1.4, -L + 1.15), 0.025, seg=6), 'wood')
        d.add(tube((-8.8 + k * 0.4, 1.4, -L + 1.15), (-8.8 + k * 0.4, 1.65, -L + 1.18), 0.05, 0.0, seg=4), 'steel')
    d.build()


# ===================== CAMPO DE BATALHA =====================
def build_battle():
    R = root('scene_battle')
    def hfn(x, f):
        r = math.hypot(x, f)
        k = max(0.0, min(1.0, (r - 9) / 10))
        return k * (1.6 * noise.noise(Vector((x * 0.08, f * 0.08, 0.3))) + 0.5 * noise.noise(Vector((x * 0.3, f * 0.3, 1.7))) + 0.9 * k) - 0.02
    g = Part('battle_ground', R)
    g.add(grid(100, 70, height_fn=hfn), 'ground')
    for i in range(34):
        a = random.uniform(0, 2 * math.pi)
        r = random.uniform(9, 28)
        x, f = math.cos(a) * r, math.sin(a) * r
        g.add(rock((x, -0.45 + hfn(x, f) - 0.402 + 0.0, f), random.uniform(0.3, 1.4)), 'rock')
    g.build()
    d = Part('battle_props', R)
    # árvores secas
    for i in range(9):
        a = random.uniform(0, 2 * math.pi)
        r = random.uniform(13, 24)
        x, f = math.cos(a) * r, math.sin(a) * r
        if f > 6:
            f = -f
        base_h = hfn(x, f) - 0.45
        hh = random.uniform(3.5, 6)
        d.add(sweep([(x, base_h, f), (x + 0.2, base_h + hh * 0.5, f + 0.1), (x - 0.1, base_h + hh, f + 0.2)], [0.28, 0.18, 0.04], seg=8), 'bark')
        for b in range(4):
            ba = random.uniform(0, 6.28)
            hb = base_h + hh * random.uniform(0.45, 0.85)
            ln = random.uniform(0.9, 1.8)
            d.add(sweep([(x, hb, f), (x + math.cos(ba) * ln * 0.6, hb + 0.5, f + math.sin(ba) * ln * 0.6), (x + math.cos(ba) * ln, hb + 0.9, f + math.sin(ba) * ln)], [0.1, 0.05, 0.01], seg=6), 'bark')
    # espadas e lanças cravadas, escudos caídos
    for i in range(22):
        a = random.uniform(0, 2 * math.pi)
        r = random.uniform(7.5, 16)
        x, f = math.cos(a) * r, math.sin(a) * r
        bh = hfn(x, f) - 0.42
        tilt_x, tilt_z = random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3)
        if i % 3 == 0:
            d.add(tube((x, bh - 0.2, f), (x + tilt_x, bh + 2.2, f + tilt_z), 0.035, seg=6), 'wood')
            d.add(tube((x + tilt_x, bh + 2.2, f + tilt_z), (x + tilt_x * 1.1, bh + 2.55, f + tilt_z * 1.1), 0.07, 0.0, seg=4), 'steel')
        elif i % 3 == 1:
            d.add(box((x, bh + 0.5, f), (0.09, 1.2, 0.02), bev=0.01, roll=tilt_x, pitch=tilt_z), 'steel')
            d.add(box((x + tilt_x * 0.5 * 0, bh + 1.15, f), (0.35, 0.06, 0.06), bev=0.01, roll=tilt_x, pitch=tilt_z), 'gold')
        else:
            d.add(xf(tube((0, 0, -0.03), (0, 0, 0.03), 0.45, seg=20), (x, bh + 0.05, f), pitch=-math.pi / 2 + 0.2), 'wood')
            d.add(xf(sphere((0, 0, 0.04), 0.1, (1, 1, 0.6), u=10, v=8), (x, bh + 0.05, f), pitch=-math.pi / 2 + 0.2), 'iron')
    # estandartes de guerra rasgados
    for i, (x, f) in enumerate([(-9, -9), (9.5, -8), (-12, 3), (12, 4)]):
        bh = hfn(x, f) - 0.42
        d.add(tube((x, bh, f), (x, bh + 5.5, f), 0.06, seg=8), 'wood')
        banner(d, (x + 0.75, bh + 5.3, f), 1.3, 2.4, 0.0, 'banner' if i % 2 else 'banner2', emblem=False)
    # muro em ruínas e tendas ao fundo
    for k in range(8):
        x = -10 + k * 1.6
        hh = random.uniform(0.8, 2.6)
        d.add(box((x, -0.4 + hh / 2, -17), (1.5, hh, 1.0), bev=0.05, yaw=random.uniform(-0.08, 0.08)), 'stone')
    for (x, f) in [(16, -18), (19, -14), (-18, -16)]:
        bh = hfn(x, f) - 0.42
        d.add(lathe([(0, bh), (2.2, bh), (0, bh + 3.0)], seg=8, off=(x, 0, f)), 'cloth')
        d.add(tube((x, bh + 2.9, f), (x, bh + 3.6, f), 0.05, seg=6), 'wood')
    d.build()


# ===================== SALÃO DO TRONO =====================
def build_throne():
    R = root('scene_throne')
    g = Part('throne_floor', R)
    g.add(grid(60, 4), 'marble')
    g.add(box((0, -0.39, -11.5), (3.2, 0.03, 13), bev=0.0), 'carpet')
    for sx in (-1, 1):
        g.add(box((sx * 1.62, -0.38, -11.5), (0.1, 0.035, 13), bev=0.0), 'gold')
    g.build()
    w = Part('throne_hall', R)
    for f in range(-18, 13, 5):
        for sx in (-1, 1):
            x = sx * 8.5
            w.add(box((x, -0.25, f), (1.4, 0.3, 1.4), bev=0.04), 'column')
            w.add(lathe([(0.55, -0.1), (0.5, 0.2), (0.45, 7.0), (0.55, 7.2), (0, 7.2)], seg=20, off=(x, 0, f), folds=12, famp=0.04, ftop=7.5), 'column')
            w.add(box((x, 7.4, f), (1.4, 0.4, 1.4), bev=0.04), 'column')
            w.add(ring((x, 7.05, f), 0.52, 0.06, seg=20, tseg=6), 'gold')
    for sx in (-1, 1):
        w.add(box((sx * 13, 4.6, -3), (0.8, 10, 32), bev=0.05), 'stone')
        for f in (-15, -8, -1, 6):
            w.add(box((sx * 12.58, 4.8, f), (0.06, 4.4, 1.8), bev=0.0), 'glass')
            w.add(ring((sx * 12.55, 7.0, f), 0.9, 0.08, plane='side', seg=16, tseg=6, a0=0, a1=math.pi), 'gold')
    w.add(box((0, 4.6, -19.4), (26, 10, 0.8), bev=0.05), 'stone')
    w.add(xf(ring((0, 0, 0), 2.2, 0.06, plane='xf', seg=40, tseg=6), (0, 6.6, -18.95)), 'gold')
    w.add(box((0, 6.6, -18.98), (0.05, 0.05, 0.05), bev=0), 'gold')
    w.build()
    t = Part('throne_seat', R)
    for i, (wd, dp) in enumerate([(7, 5.5), (5.5, 4.2), (4.2, 3.0)]):
        t.add(box((0, -0.4 + 0.25 + i * 0.5, -16.6 + i * 0.3), (wd, 0.5, dp), bev=0.04), 'column')
        t.add(box((0, -0.4 + 0.5 + i * 0.5, -16.6 + i * 0.3 + dp / 2), (wd, 0.04, 0.06), bev=0.0), 'gold')
    fh = 1.1
    t.add(box((0, fh + 0.4, -16.4), (1.6, 0.25, 1.3), bev=0.05), 'gold')
    t.add(box((0, fh + 0.6, -16.35), (1.4, 0.18, 1.1), bev=0.06), 'velvet')
    t.add(box((0, fh + 2.0, -17.0), (1.6, 3.0, 0.25), bev=0.06), 'gold')
    t.add(box((0, fh + 1.9, -16.86), (1.25, 2.4, 0.06), bev=0.03), 'velvet')
    for sx in (-1, 1):
        t.add(box((sx * 0.85, fh + 0.95, -16.4), (0.18, 0.9, 1.3), bev=0.04), 'gold')
        t.add(sphere((sx * 0.85, fh + 1.45, -15.8), 0.12, u=12, v=8), 'gold')
        t.add(tube((sx * 0.8, fh + 3.5, -17.0), (sx * 0.8, fh + 3.9, -17.0), 0.1, 0.0, seg=8), 'gold')
    t.add(sphere((0, fh + 3.65, -17.0), 0.22, u=16, v=10), 'gold')
    for sx in (-1, 1):
        for f in (-13.5, -9.0):
            t.add(lathe([(0, -0.4), (0.4, -0.4), (0.12, 0.2), (0.1, 1.6), (0.5, 1.9), (0.55, 2.1), (0, 2.0)], seg=14, off=(sx * 3.2, 0, f)), 'iron')
            t.add(sphere((sx * 3.2, 2.35, f), 0.3, (1, 1.6, 1), u=10, v=8), 'flame')
            empty(f'light_brazier_{sx}_{int(f)}', t, (sx * 3.2, 2.6, f))
    for i, f in enumerate((-15.5, -10.5, -5.5, -0.5, 4.5)):
        for sx in (-1, 1):
            banner(t, (sx * 12.5, 8.6, f + 2.5), 1.5, 3.2, -sx * math.pi / 2, 'banner' if (i + (sx > 0)) % 2 == 0 else 'banner2')
    banner(t, (0, 9.2, -18.9), 3.2, 5.0, 0.0, 'banner')
    t.build()


build_castle(); build_battle(); build_throne()
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_apply=True, export_yup=True,
                          export_texcoords=True, export_normals=True, export_materials='EXPORT')
tris = 0
for o in bpy.data.objects:
    if o.type == 'MESH':
        o.data.calc_loop_triangles(); tris += len(o.data.loop_triangles)
print('OK', OUT, 'tris', tris)
