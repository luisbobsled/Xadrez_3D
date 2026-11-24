"""Modela as 6 peças do Xadrez de Batalha 3D no Blender e exporta um GLB.
Coordenadas de modelagem em "estilo three": (x, h=altura, f=frente). P() converte para Blender (Z para cima, frente = -Y).
"""
import bpy, bmesh, math, sys, random
from mathutils import Vector, Matrix

random.seed(7)
# cria uma cena nova (não mexe no que já está aberto)
scene = bpy.data.scenes.new('Xadrez')
try:
    bpy.context.window.scene = scene
except Exception:
    pass
import os
OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else os.path.join(os.path.expanduser('~'), 'Documents', 'xadrez3d', 'pieces_v2.glb')
os.makedirs(os.path.dirname(OUT), exist_ok=True)

COL = {
    'eyew': (0.97, 0.96, 0.93, 1), 'mouth': (0.35, 0.08, 0.08, 1),
    'main': (0.92, 0.86, 0.74, 1), 'trim': (0.85, 0.62, 0.18, 1), 'dark': (0.35, 0.22, 0.12, 1),
    'skin': (0.95, 0.76, 0.62, 1), 'hair': (0.6, 0.42, 0.12, 1), 'cape': (0.62, 0.07, 0.12, 1),
    'steel': (0.86, 0.88, 0.92, 1), 'iron': (0.18, 0.18, 0.2, 1), 'fur': (1, 1, 1, 1),
    'lips': (0.7, 0.14, 0.2, 1), 'eye': (0.02, 0.02, 0.02, 1), 'gem': (0.2, 0.4, 1, 1),
}
METAL = {'trim': 0.9, 'steel': 1.0, 'iron': 0.85}
MATS = {}


def mat(n):
    if n not in MATS:
        m = bpy.data.materials.new(n)
        try:
            m.use_nodes = True
        except Exception:
            pass
        b = m.node_tree.nodes.get('Principled BSDF') if m.node_tree else None
        if b:
            b.inputs['Base Color'].default_value = COL[n]
            b.inputs['Metallic'].default_value = METAL.get(n, 0.0)
            b.inputs['Roughness'].default_value = 0.3 if n in METAL else 0.55
        MATS[n] = m
    return MATS[n]


def P(x, h, f):
    return Vector((x, -f, h))


def V3(t):
    return P(*t)


def finish(bm, sharp=math.radians(42)):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        if len(e.link_faces) == 2:
            try:
                if e.calc_face_angle(0) > sharp:
                    e.smooth = False
            except Exception:
                pass


class Part:
    def __init__(self, name, parent=None, loc=(0, 0, 0)):
        self.name, self.parent, self.loc = name, parent, loc
        self.bm = bmesh.new()
        self.mats = []
        self.obj = None

    def add(self, bm, m):
        finish(bm)
        if m not in self.mats:
            self.mats.append(m)
        idx = self.mats.index(m)
        me = bpy.data.meshes.new('tmp')
        bm.to_mesh(me)
        bm.free()
        n = len(self.bm.faces)
        self.bm.from_mesh(me)
        self.bm.faces.ensure_lookup_table()
        for f in self.bm.faces[n:]:
            f.material_index = idx
        bpy.data.meshes.remove(me)
        return self

    def add_abs(self, bm, m):
        bmesh.ops.translate(bm, vec=-V3(self.loc), verts=bm.verts)
        return self.add(bm, m)

    def build(self):
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(mat(m))
        o = bpy.data.objects.new(self.name, me)
        scene.collection.objects.link(o)
        if self.parent is not None:
            o.parent = self.parent.obj if isinstance(self.parent, Part) else self.parent
        o.location = V3(self.loc)
        self.obj = o
        return o


def empty(name, parent, loc):
    o = bpy.data.objects.new(name, None)
    scene.collection.objects.link(o)
    o.parent = parent.obj if isinstance(parent, Part) else parent
    o.location = V3(loc)
    return o


# ---------- construtores de geometria (retornam bmesh) ----------
def xf(bm, loc=(0, 0, 0), yaw=0.0, pitch=0.0, roll=0.0):
    # pitch: inclina o topo para a frente; yaw: gira em torno do eixo vertical; roll: em torno do eixo frente
    M = Matrix.Translation(V3(loc)) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(pitch, 4, 'X') @ Matrix.Rotation(-roll, 4, 'Y')
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    return bm


def lathe(prof, seg=36, folds=0, famp=0.0, ftop=None, sf=1.0, sx=1.0, off=(0, 0, 0), a0=None, a1=None, rnd=0.0):
    """Perfil (r,h) girado em torno do eixo vertical. a0/a1 = arco aberto (lençol). folds = dobras de tecido."""
    bm = bmesh.new()
    hmin = min(h for r, h in prof)
    open_arc = a0 is not None
    n = seg + 1 if open_arc else seg
    phase = [random.uniform(0, 6.28) for _ in range(3)]
    rings = []
    for r, h in prof:
        if r < 1e-6 and not open_arc:
            rings.append([bm.verts.new(P(off[0], h + off[1], off[2]))])
            continue
        ring = []
        for i in range(n):
            a = (a0 + (a1 - a0) * i / seg) if open_arc else 2 * math.pi * i / seg
            rr = r
            if folds and ftop is not None and h < ftop:
                t = (ftop - h) / max(1e-6, (ftop - hmin))
                rr = r * (1 + famp * t * (math.sin(a * folds + phase[0]) + 0.35 * math.sin(a * folds * 2.3 + phase[1])))
            if rnd:
                rr *= 1 + rnd * math.sin(a * 7 + h * 40 + phase[2])
            ring.append(bm.verts.new(P(off[0] + rr * math.cos(a) * sx, off[1] + h, off[2] + rr * math.sin(a) * sf)))
        rings.append(ring)
    for A, B in zip(rings, rings[1:]):
        if len(A) == 1 and len(B) == 1:
            continue
        rng = range(n - 1) if open_arc else range(n)
        for i in rng:
            j = (i + 1) % n
            if len(A) == 1:
                bm.faces.new((A[0], B[j], B[i]))
            elif len(B) == 1:
                bm.faces.new((A[i], A[j], B[0]))
            else:
                bm.faces.new((A[i], A[j], B[j], B[i]))
    if not open_arc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def sphere(c, r, scale=(1, 1, 1), u=24, v=14, pitch=0.0, yaw=0.0):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=1)
    S = Matrix.Diagonal((r * scale[0], r * scale[2], r * scale[1], 1))
    bmesh.ops.transform(bm, matrix=S, verts=bm.verts)
    return xf(bm, c, yaw=yaw, pitch=pitch)


def tube(p1, p2, r1, r2=None, seg=16, caps=True):
    r2 = r1 if r2 is None else r2
    a, b = V3(p1), V3(p2)
    d = b - a
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=r1, radius2=r2, depth=d.length)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    M = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    return bm


def box(c, dims, bev=0.004, yaw=0.0, pitch=0.0, roll=0.0):
    """dims = (largura x, altura h, profundidade f)"""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.transform(bm, matrix=Matrix.Diagonal((dims[0], dims[2], dims[1], 1)), verts=bm.verts)
    if bev > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=min(bev, min(dims) * 0.45), segments=2, affect='EDGES', profile=0.5)
    return xf(bm, c, yaw=yaw, pitch=pitch, roll=roll)


def sweep(pts, radii, seg=10, closed=False, flat=1.0):
    """Tubo ao longo de uma linha (para cabelo, cauda, báculo, arcos da coroa...)."""
    pts = [V3(p) for p in pts]
    n = len(pts)
    if not isinstance(radii, (list, tuple)):
        radii = [radii] * n
    bm = bmesh.new()
    rings = []
    prev = None
    for i, p in enumerate(pts):
        if closed:
            t = (pts[(i + 1) % n] - pts[(i - 1) % n]).normalized()
        else:
            t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        if prev is None:
            ax = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            nn = t.cross(ax).normalized()
        else:
            nn = (prev - t * prev.dot(t))
            nn = nn.normalized() if nn.length > 1e-6 else prev
        bb = t.cross(nn)
        prev = nn
        r = radii[i]
        if r <= 1e-6:
            rings.append([bm.verts.new(p)])
        else:
            rings.append([bm.verts.new(p + (nn * math.cos(2 * math.pi * k / seg) * flat + bb * math.sin(2 * math.pi * k / seg)) * r) for k in range(seg)])
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for A, B in pairs:
        for k in range(seg):
            j = (k + 1) % seg
            if len(A) == 1 and len(B) == 1:
                continue
            if len(A) == 1:
                bm.faces.new((A[0], B[k], B[j]))
            elif len(B) == 1:
                bm.faces.new((A[k], A[j], B[0]))
            else:
                bm.faces.new((A[k], A[j], B[j], B[k]))
    if not closed:
        for R in (rings[0], rings[-1]):
            if len(R) > 2:
                bm.faces.new(R)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def ring(c, R, r, plane='h', seg=40, tseg=10, a0=0.0, a1=2 * math.pi):
    closed = abs(a1 - a0 - 2 * math.pi) < 1e-6
    cnt = seg if closed else seg + 1
    pts = []
    for i in range(cnt):
        a = a0 + (a1 - a0) * i / seg
        if plane == 'h':   # anel horizontal
            pts.append((c[0] + R * math.cos(a), c[1], c[2] + R * math.sin(a)))
        elif plane == 'xf':  # vertical, de frente (plano x-h)
            pts.append((c[0] + R * math.cos(a), c[1] + R * math.sin(a), c[2]))
        else:  # 'side' plano f-h
            pts.append((c[0], c[1] + R * math.sin(a), c[2] + R * math.cos(a)))
    return sweep(pts, r, seg=tseg, closed=closed)


def metaball_mesh(balls, res=0.011, thr=0.6):
    mb = bpy.data.metaballs.new('mb')
    mb.resolution = res
    mb.render_resolution = res
    mb.threshold = thr
    mo = bpy.data.objects.new('mb', mb)
    scene.collection.objects.link(mo)
    for c, r in balls:
        e = mb.elements.new()
        e.co = V3(c)
        e.radius = r
        e.stiffness = 2.0
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(mo.evaluated_get(dg))
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    bpy.data.objects.remove(mo)
    bpy.data.metaballs.remove(mb)
    return bm


def chain(a, b, ra, rb, n):
    return [(tuple(a[k] + (b[k] - a[k]) * i / (n - 1) for k in range(3)), ra + (rb - ra) * i / (n - 1)) for i in range(n)]


def root(name):
    o = bpy.data.objects.new(name, None)
    scene.collection.objects.link(o)
    return o


def base(part, r):
    part.add(lathe([(0, 0), (r, 0), (r, 0.022), (r - 0.006, 0.03), (r - 0.022, 0.036), (r - 0.022, 0.052),
                    (r - 0.036, 0.06), (r - 0.058, 0.074), (r - 0.07, 0.088), (r - 0.075, 0.09), (0, 0.09)], seg=48), 'main')
    part.add(ring((0, 0.043, 0), r - 0.019, 0.01, seg=56, tseg=8), 'trim')
    part.add(ring((0, 0.081, 0), r - 0.064, 0.006, seg=56, tseg=6), 'trim')


def face(part, hc, hr, f_ext, eye_sp=0.027, nose=True, ears=True, brows=None, mouth=True):
    """olhos, nariz, orelhas e sobrancelhas numa cabeça de centro (0,hc,0) e raio hr"""
    for s in (-1, 1):
        part.add(sphere((s * eye_sp, hc + 0.008, hr * 0.83), 0.0155, (1.1, 0.95, 0.55), u=14, v=10), 'eyew')
        part.add(sphere((s * eye_sp, hc + 0.007, hr * 0.83 + 0.007), 0.0085, (1, 1, 0.5), u=12, v=8), 'eye')
        part.add(box((s * eye_sp, hc + 0.017, hr * 0.84), (0.026, 0.004, 0.012), bev=0.001, pitch=-0.3), 'skin')
        if ears:
            part.add(sphere((s * hr * 0.98, hc, 0), 0.016, (0.6, 1.3, 1), u=10, v=8), 'skin')
        if brows:
            part.add(box((s * eye_sp, hc + 0.03, hr * 0.88), (0.026, 0.007, 0.008), bev=0.002, roll=-s * 0.18), brows)
    if nose:
        part.add(sphere((0, hc - 0.008, hr * 0.98), 0.014, (0.8, 1.3, 1.0), u=12, v=8), 'skin')
    if mouth:
        part.add(sphere((0, hc - 0.034, hr * 0.9), 0.012, (1.5, 0.35, 0.5), u=12, v=8), 'mouth')


def hand(part, c, r):
    part.add(sphere(c, r, (0.85, 1.2, 0.9), u=14, v=10), 'skin')
    part.add(sphere((c[0], c[1] + r * 0.25, c[2] + r * 0.75), r * 0.42, (0.8, 1.4, 0.8), u=10, v=8, pitch=0.5), 'skin')


# ===================== PEÃO: soldado =====================
def build_pawn():
    R = root('piece_p')
    b = Part('p_body', R)
    base(b, 0.3)
    for s in (-1, 1):
        b.add(tube((s * 0.052, 0.16, 0), (s * 0.052, 0.27, 0), 0.04, 0.042, seg=14), 'dark')
        b.add(tube((s * 0.052, 0.09, 0.005), (s * 0.052, 0.17, 0), 0.045, 0.043, seg=14), 'dark')
        b.add(sphere((s * 0.052, 0.105, 0.035), 0.045, (0.95, 0.6, 1.25), u=14, v=10), 'dark')
        b.add(ring((s * 0.052, 0.168, 0), 0.044, 0.006, seg=20, tseg=6), 'trim')
    b.add(lathe([(0, 0.2), (0.142, 0.2), (0.148, 0.208), (0.13, 0.27), (0.113, 0.32), (0.109, 0.4), (0.118, 0.445),
                 (0.102, 0.478), (0.06, 0.498), (0, 0.5)], seg=40, folds=9, famp=0.07, ftop=0.31), 'main')
    b.add(ring((0, 0.205, 0), 0.146, 0.007, seg=48, tseg=6), 'trim')
    b.add(ring((0, 0.325, 0), 0.113, 0.013, seg=40, tseg=8), 'dark')
    b.add(box((0, 0.325, 0.122), (0.034, 0.032, 0.012), bev=0.003), 'trim')
    b.add(sphere((0, 0.405, 0.012), 0.11, (1.0, 0.75, 0.95), u=28, v=14), 'steel')
    b.add(box((0, 0.41, 0.115), (0.012, 0.07, 0.01), bev=0.003), 'trim')
    for s in (-1, 1):
        b.add(sphere((s * 0.125, 0.46, 0), 0.05, (1.05, 0.75, 1.0), u=16, v=10), 'steel')
    b.add(tube((0, 0.48, 0), (0, 0.53, 0), 0.032, 0.03, seg=14), 'skin')
    b.add(sphere((0, 0.565, 0), 0.074, (1, 1.06, 1), u=24, v=16), 'skin')
    face(b, 0.565, 0.074, 0.074, brows='dark')
    b.add(lathe([(0, 0.668), (0.03, 0.663), (0.058, 0.648), (0.077, 0.625), (0.086, 0.6), (0.088, 0.578), (0.0, 0.578)], seg=36), 'steel')
    b.add(ring((0, 0.578, 0), 0.09, 0.009, seg=40, tseg=6), 'steel')
    b.add(box((0, 0.552, 0.083), (0.012, 0.062, 0.01), bev=0.003), 'steel')
    for s in (-1, 1):
        b.add(box((s * 0.07, 0.548, 0.025), (0.01, 0.055, 0.045), bev=0.003, yaw=s * 0.3), 'steel')
    # escudo (lado esquerdo)
    sh = bmesh.new()
    parts = [
        (tube((0, 0, -0.012), (0, 0, 0.012), 0.105, seg=36), 'trim'),
        (tube((0, 0, 0.012), (0, 0, 0.016), 0.088, seg=36), 'cape'),
        (box((0, 0, 0.019), (0.022, 0.15, 0.006), bev=0.002), 'trim'),
        (box((0, 0.012, 0.019), (0.12, 0.022, 0.006), bev=0.002), 'trim'),
        (sphere((0, 0, 0.022), 0.024, (1, 1, 0.7), u=14, v=10), 'steel'),
        (ring((0, 0, 0.008), 0.104, 0.008, plane='xf', seg=40, tseg=6), 'steel'),
    ]
    for g, m in parts:
        xf(g, (-0.165, 0.36, 0.06), yaw=-0.45)
        b.add(g, m)
    b.add(tube((-0.13, 0.46, 0), (-0.165, 0.37, 0.02), 0.032, 0.029, seg=12), 'main')
    b.add(tube((-0.165, 0.37, 0.02), (-0.15, 0.33, 0.07), 0.028, 0.025, seg=12), 'main')
    # bainha na cintura direita
    b.add(tube((0.118, 0.33, -0.05), (0.165, 0.15, -0.085), 0.017, 0.012, seg=10), 'dark')
    b.add(sphere((0.166, 0.147, -0.086), 0.014, u=10, v=8), 'trim')
    b.add(ring((0.122, 0.315, -0.053), 0.019, 0.004, seg=14, tseg=5), 'trim')
    b.build()
    pl = Part('p_plume', b, (0, 0.66, 0.02))
    pl.add_abs(sweep([(0, 0.655, 0.05), (0, 0.69, 0.025), (0, 0.708, -0.02), (0, 0.698, -0.07), (0, 0.665, -0.105), (0, 0.62, -0.12)],
                [0.012, 0.02, 0.025, 0.024, 0.017, 0.006], seg=10, flat=0.5), 'cape')
    pl.build()
    hilt = Part('p_hilt', b)
    hilt.add(box((0.116, 0.345, -0.048), (0.07, 0.012, 0.02), bev=0.003, roll=0.25), 'trim')
    hilt.add(tube((0.114, 0.35, -0.047), (0.102, 0.4, -0.04), 0.009, seg=8), 'dark')
    hilt.add(sphere((0.1, 0.41, -0.039), 0.014, u=10, v=8), 'trim')
    hilt.build()
    arm = Part('p_arm', b, (0.135, 0.455, 0))
    arm.add(sphere((0, 0, 0), 0.036, u=14, v=10), 'main')
    arm.add(tube((0, 0, 0), (0.008, -0.09, 0), 0.033, 0.03, seg=12), 'main')
    arm.add(tube((0.008, -0.09, 0), (0.01, -0.165, 0), 0.03, 0.026, seg=12), 'main')
    arm.add(tube((0.009, -0.105, 0), (0.01, -0.16, 0), 0.032, 0.029, seg=12), 'steel')
    hand(arm, (0.01, -0.18, 0), 0.027)
    arm.build()
    sw = Part('p_sword', arm, (0.01, -0.18, 0))
    sw.add(tube((0, 0.035, 0), (0, -0.02, 0), 0.009, seg=8), 'dark')
    sw.add(sphere((0, 0.045, 0), 0.014, u=10, v=8), 'trim')
    sw.add(box((0, -0.03, 0), (0.1, 0.014, 0.022), bev=0.004), 'trim')
    for s in (-1, 1):
        sw.add(sphere((s * 0.05, -0.03, 0), 0.01, u=8, v=6), 'trim')
    sw.add(box((0, -0.175, 0), (0.03, 0.27, 0.008), bev=0.003), 'steel')
    sw.add(box((0, -0.16, 0.0042), (0.006, 0.22, 0.002), bev=0.0008), 'iron')
    sw.add(tube((0, -0.309, 0), (0, -0.36, 0), 0.0212, 0.0, seg=4), 'steel')
    sw.build()


# ===================== TORRE: torre de castelo =====================
def build_rook():
    R = root('piece_r')
    b = Part('r_body', R)
    base(b, 0.37)
    rad = lambda h: 0.256 - 0.024 * (h - 0.17) / 0.43 + 0.004 * math.sin((h - 0.17) / 0.43 * math.pi)
    prof = [(0, 0.09), (0.3, 0.09), (0.3, 0.115), (0.29, 0.122), (0.282, 0.14), (0.27, 0.15), (0.262, 0.165)]
    prof += [(rad(h), h) for h in [0.17 + 0.43 * i / 8 for i in range(9)]]
    prof += [(0.246, 0.615), (0.262, 0.635), (0.278, 0.655), (0.284, 0.67), (0.284, 0.72), (0.244, 0.72), (0.244, 0.705), (0, 0.705)]
    b.add(lathe(prof, seg=48), 'main')
    for i in range(8):
        a = i * math.pi / 4 + math.pi / 8
        b.add(box((math.sin(a) * 0.262, 0.762, math.cos(a) * 0.262), (0.105, 0.085, 0.042), bev=0.006, yaw=a), 'main')
    for i in range(16):
        a = i * math.pi / 8
        b.add(box((math.sin(a) * 0.255, 0.625, math.cos(a) * 0.255), (0.03, 0.04, 0.035), bev=0.004, yaw=a), 'main')
    for h in (0.25, 0.34, 0.43, 0.52):
        b.add(ring((0, h, 0), rad(h) + 0.0015, 0.0035, seg=56, tseg=5), 'dark')
    for row, h in enumerate((0.205, 0.295, 0.385, 0.475, 0.56)):
        for i in range(12):
            a = (i + 0.5 * (row % 2)) * math.pi / 6
            if abs(math.sin(a / 2) ) < 0.2 and h < 0.5:
                continue
            b.add(box((math.sin(a) * (rad(h) + 0.001), h, math.cos(a) * (rad(h) + 0.001)), (0.006, 0.08, 0.006), bev=0, yaw=a), 'dark')
    # porta em arco com tábuas e ferragens
    b.add(box((0, 0.215, 0.244), (0.11, 0.13, 0.03), bev=0.002), 'dark')
    b.add(tube((0, 0.28, 0.229), (0, 0.28, 0.259), 0.055, seg=24), 'dark')
    for x in (-0.028, 0, 0.028):
        b.add(box((x, 0.24, 0.26), (0.003, 0.16, 0.003), bev=0), 'iron')
    for h in (0.19, 0.25):
        b.add(box((0, h, 0.261), (0.112, 0.009, 0.005), bev=0.001), 'iron')
    b.add(ring((0.035, 0.23, 0.265), 0.01, 0.0025, plane='xf', seg=12, tseg=4), 'trim')
    b.add(ring((0, 0.28, 0.252), 0.066, 0.012, plane='xf', seg=24, tseg=8, a0=0, a1=math.pi), 'main')
    for s in (-1, 1):
        b.add(box((s * 0.066, 0.215, 0.252), (0.024, 0.13, 0.024), bev=0.004), 'main')
    # seteiras
    for a in (math.pi / 2, -math.pi / 2, math.pi, 3 * math.pi / 4, -3 * math.pi / 4):
        r = rad(0.47)
        b.add(box((math.sin(a) * r, 0.47, math.cos(a) * r), (0.018, 0.085, 0.03), bev=0.002, yaw=a), 'dark')
        b.add(box((math.sin(a) * r, 0.47, math.cos(a) * r), (0.05, 0.016, 0.03), bev=0.002, yaw=a), 'dark')
    b.add(box((0, 0.46, 0.236), (0.12, 0.1, 0.03), bev=0.004), 'dark')
    b.add(tube((0, 0.705, 0), (0, 1.0, 0), 0.008, seg=8), 'dark')
    b.add(sphere((0, 1.005, 0), 0.016, u=12, v=8), 'trim')
    b.build()
    cg = Part('r_cannon', b, (0, 0.46, 0.2))
    cg.add(sweep([(0, 0, -0.04), (0, 0, 0.0), (0, 0, 0.06), (0, 0, 0.13), (0, 0, 0.17), (0, 0, 0.19), (0, 0, 0.205)],
                 [0.03, 0.05, 0.047, 0.042, 0.039, 0.046, 0.044], seg=20), 'iron')
    for f in (0.03, 0.12):
        cg.add(ring((0, 0, f), 0.049 - f * 0.05, 0.007, plane='side', seg=24, tseg=6), 'trim')
    cg.add(tube((0, 0, 0.2), (0, 0, 0.207), 0.026, seg=16), 'eye')
    cg.add(sphere((0, 0, -0.045), 0.02, u=10, v=8), 'iron')
    cg.build()
    empty('r_muzzle', cg, (0, 0, 0.21))
    fl = Part('r_flag', b, (0, 0.95, 0))
    bm = bmesh.new()
    nx, nh = 12, 5
    vs = [[bm.verts.new(P(0.14 * i / nx, -0.04 + 0.08 * j / nh, 0.012 * math.sin(i / nx * 7) * (i / nx))) for j in range(nh + 1)] for i in range(nx + 1)]
    for i in range(nx):
        for j in range(nh):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
    fl.add(bm, 'cape')
    fl.build()


# ===================== CAVALO: um cavalo de verdade =====================
def build_knight():
    R = root('piece_n')
    b = Part('n_base', R)
    base(b, 0.34)
    b.build()
    rear = Part('n_rear', b, (0, 0.09, -0.17))
    rear.build()
    h = Part('n_horse', rear, (0, -0.09, 0.17))
    balls = []
    balls += chain((0, 0.43, -0.17), (0, 0.44, 0.15), 0.15, 0.155, 7)        # tronco
    balls += [((0, 0.4, 0.0), 0.15), ((0, 0.415, 0.16), 0.15), ((0, 0.45, -0.18), 0.145)]
    balls += chain((0, 0.5, 0.17), (0, 0.69, 0.29), 0.115, 0.085, 6)         # pescoço
    balls += chain((0, 0.72, 0.31), (0, 0.635, 0.45), 0.085, 0.06, 6)        # cabeça
    balls += [((0, 0.74, 0.3), 0.08)]
    for s in (-1, 1):
        balls += chain((s * 0.07, 0.37, 0.16), (s * 0.072, 0.24, 0.17), 0.07, 0.05, 4)    # pata dianteira
        balls += chain((s * 0.072, 0.24, 0.17), (s * 0.072, 0.13, 0.165), 0.048, 0.042, 4)
        balls += chain((s * 0.075, 0.4, -0.15), (s * 0.075, 0.27, -0.19), 0.095, 0.055, 4)   # coxa traseira
        balls += chain((s * 0.075, 0.26, -0.19), (s * 0.073, 0.13, -0.165), 0.05, 0.042, 4)
    h.add(metaball_mesh(balls, res=0.0095), 'main')
    for s in (-1, 1):
        for f in (0.165, -0.165):
            h.add(tube((s * 0.072, 0.09, f), (s * 0.072, 0.125, f), 0.036, 0.031, seg=14), 'dark')
        ear = sphere((s * 0.033, 0.815, 0.305), 0.022, (0.7, 2.2, 0.8), u=10, v=8, pitch=-0.2)
        h.add(ear, 'main')
        h.add(sphere((s * 0.06, 0.735, 0.37), 0.014, u=10, v=8), 'eye')
        h.add(sphere((s * 0.022, 0.625, 0.487), 0.009, u=8, v=6), 'eye')
    # crina e topete
    for i in range(10):
        t = i / 9
        c = (0, 0.79 - 0.27 * t, 0.27 - 0.2 * t)
        h.add(sphere(c, 0.05 - 0.012 * t, (0.28, 1.0, 0.55), u=12, v=8, pitch=0.9 + random.uniform(-0.15, 0.15)), 'hair')
    h.add(sphere((0, 0.79, 0.345), 0.035, (0.4, 0.6, 1.0), u=10, v=8, pitch=0.6), 'hair')
    # sela, manta, estribos e rédeas
    h.add(lathe([(0.0, 0.0)], seg=4) if False else sphere((0, 0.565, -0.01), 0.16, (0.92, 0.17, 0.85), u=24, v=10), 'cape')
    h.add(sphere((0, 0.588, -0.01), 0.1, (0.82, 0.25, 0.95), u=20, v=10), 'dark')
    h.add(sphere((0, 0.61, 0.07), 0.025, (1, 1.1, 0.8), u=10, v=8), 'trim')
    h.add(sphere((0, 0.612, -0.085), 0.045, (1.2, 0.5, 0.4), u=12, v=8), 'dark')
    for s in (-1, 1):
        h.add(box((s * 0.138, 0.47, -0.01), (0.006, 0.14, 0.014), bev=0, roll=s * 0.05), 'dark')
        h.add(ring((s * 0.142, 0.39, -0.01), 0.018, 0.004, plane='xf', seg=14, tseg=5), 'trim')
        h.add(sweep([(s * 0.045, 0.64, 0.45), (s * 0.075, 0.6, 0.36), (s * 0.06, 0.6, 0.18), (s * 0.03, 0.62, 0.08)], 0.004, seg=5), 'dark')
    h.add(ring((0, 0.655, 0.44), 0.05, 0.007, plane='side', seg=24, tseg=6), 'trim')
    h.add(sweep([(0.045, 0.66, 0.43), (0.05, 0.72, 0.36), (0, 0.775, 0.3), (-0.05, 0.72, 0.36), (-0.045, 0.66, 0.43)], 0.005, seg=5), 'trim')
    h.build()
    tl = Part('n_tail', h, (0, 0.5, -0.26))
    for dx in (-0.014, -0.005, 0.005, 0.014):
        tl.add_abs(sweep([(dx, 0.5, -0.26), (dx * 1.5, 0.48, -0.31), (dx * 2, 0.4, -0.345), (dx * 2.5, 0.29, -0.335), (dx * 3, 0.19, -0.31)],
                    [0.02, 0.024, 0.02, 0.013, 0.003], seg=8), 'hair')
    tl.build()


# ===================== BISPO =====================
def build_bishop():
    R = root('piece_b')
    b = Part('b_body', R)
    base(b, 0.34)
    rprof = [(0.232, 0.09), (0.233, 0.1), (0.212, 0.2), (0.186, 0.3), (0.163, 0.42), (0.147, 0.52), (0.137, 0.6), (0.132, 0.66), (0.09, 0.7), (0.04, 0.715)]
    b.add(lathe([(0, 0.09)] + rprof + [(0, 0.716)], seg=48, folds=11, famp=0.05, ftop=0.45), 'main')
    def rr(hh):
        for (r1, h1), (r2, h2) in zip(rprof, rprof[1:]):
            if h1 <= hh <= h2:
                return r1 + (r2 - r1) * (hh - h1) / (h2 - h1)
        return rprof[-1][0]
    hs = [0.22 + 0.46 * i / 10 for i in range(11)]
    # casula (vestimenta da frente) e capa
    b.add(lathe([(rr(hh) + 0.012, hh) for hh in hs], seg=20, a0=0.27 * math.pi, a1=0.73 * math.pi, folds=5, famp=0.03, ftop=0.45), 'cape')
    for a in (0.27 * math.pi, 0.73 * math.pi):
        b.add(sweep([((rr(hh) + 0.014) * math.cos(a), hh, (rr(hh) + 0.014) * math.sin(a)) for hh in hs], 0.007, seg=6), 'trim')
    b.add(sweep([(0, hh, rr(hh) + 0.016) for hh in hs[1:]], 0.009, seg=6, flat=0.4), 'trim')
    b.add(box((0, 0.56, rr(0.56) + 0.02), (0.08, 0.016, 0.006), bev=0.002, pitch=-0.15), 'trim')
    b.add(ring((0, 0.218, 0), rr(0.218) + 0.012, 0.007, seg=48, tseg=5), 'trim')
    b.add(ring((0, 0.47, 0), rr(0.47) + 0.002, 0.012, seg=40, tseg=6), 'trim')
    # mozeta (capinha dos ombros)
    b.add(lathe([(0.07, 0.725), (0.11, 0.705), (0.15, 0.665), (0.168, 0.625), (0.165, 0.615)], seg=40), 'cape')
    b.add(ring((0, 0.616, 0), 0.165, 0.006, seg=40, tseg=5), 'trim')
    b.add(tube((0, 0.7, 0), (0, 0.75, 0), 0.03, 0.028, seg=12), 'skin')
    b.add(sphere((0, 0.785, 0), 0.07, (1, 1.07, 1), u=24, v=16), 'skin')
    face(b, 0.785, 0.07, 0.07, brows='hair')
    mit = lathe([(0, 0.825), (0.079, 0.825), (0.084, 0.86), (0.084, 0.9), (0.071, 0.975), (0.045, 1.03), (0.02, 1.058), (0, 1.066)], seg=36, sf=0.7)
    b.add(mit, 'main')
    b.add(lathe([(0.083, 0.824), (0.087, 0.832), (0.087, 0.856), (0.083, 0.862), (0.083, 0.824)], seg=36, sf=0.7), 'trim')
    b.add(sweep([(0, 0.858, 0.062), (0, 0.9, 0.061), (0, 0.97, 0.05), (0, 1.03, 0.032), (0, 1.058, 0.014)], 0.008, seg=6, flat=0.4), 'trim')
    b.add(sweep([(0, 0.858, -0.062), (0, 0.9, -0.061), (0, 0.97, -0.05), (0, 1.03, -0.032), (0, 1.058, -0.014)], 0.008, seg=6, flat=0.4), 'trim')
    b.add(box((0, 0.93, 0.058), (0.05, 0.012, 0.008), bev=0.002, pitch=-0.25), 'trim')
    b.add(sphere((0, 0.88, 0.063), 0.013, u=12, v=8), 'gem')
    for s in (-1, 1):
        b.add(box((s * 0.035, 0.75, -0.07), (0.024, 0.16, 0.005), bev=0.002, pitch=0.12), 'trim')
    # braço direito em bênção (estático)
    b.add(sphere((0.13, 0.63, 0), 0.04, u=14, v=10), 'main')
    b.add(tube((0.13, 0.63, 0), (0.16, 0.53, 0.07), 0.036, 0.05, seg=16), 'main')
    b.add(ring((0.16, 0.53, 0.07), 0.05, 0.008, plane='h', seg=20, tseg=5), 'trim')
    hand(b, (0.163, 0.535, 0.105), 0.026)
    b.build()
    bcp = Part('b_cape', b, (0, 0.68, 0))
    bcp.add_abs(lathe([(rr(hh) + 0.016 + 0.05 * (0.68 - hh), hh) for hh in hs], seg=28, a0=0.98 * math.pi, a1=2.02 * math.pi, folds=7, famp=0.06, ftop=0.5), 'cape')
    bcp.build()
    arm = Part('b_staffArm', b, (-0.15, 0.63, 0))
    arm.add(sphere((0, 0, 0), 0.04, u=14, v=10), 'main')
    arm.add(tube((0, 0, 0), (0, -0.17, 0), 0.036, 0.048, seg=16), 'main')
    arm.add(ring((0, -0.168, 0), 0.048, 0.008, seg=20, tseg=5), 'trim')
    hand(arm, (0, -0.19, 0), 0.026)
    arm.build()
    st = Part('b_staff', arm, (0, -0.19, 0))
    st.add(tube((0, -0.4, 0), (0, 0.6, 0), 0.012, seg=10), 'trim')
    st.add(sphere((0, 0.43, 0), 0.022, (1, 1.3, 1), u=12, v=10), 'trim')
    st.add(ring((0, 0.47, 0), 0.016, 0.005, seg=14, tseg=5), 'trim')
    pts = [(0, 0.6, 0), (0, 0.65, 0)]
    for i in range(1, 22):
        th = math.pi - i / 21 * 1.75 * math.pi
        Rr = 0.05 - 0.022 * i / 21
        pts.append((0.05 + Rr * math.cos(th), 0.68 + Rr * math.sin(th), 0))
    st.add(sweep(pts, [0.013] * 3 + [0.013 - 0.004 * i / len(pts) for i in range(len(pts) - 3)], seg=10), 'trim')
    for th in (2.2, 1.2, 0.2):
        st.add(sphere((0.05 + 0.058 * math.cos(th), 0.68 + 0.058 * math.sin(th), 0), 0.009, u=8, v=6), 'gem')
    st.build()
    empty('b_tip', st, (0.05, 0.69, 0))


# ===================== RAINHA =====================
def build_queen():
    R = root('piece_q')
    b = Part('q_body', R)
    base(b, 0.34)
    sk = [(0.27, 0.09), (0.272, 0.1), (0.256, 0.14), (0.222, 0.22), (0.183, 0.3), (0.143, 0.4), (0.112, 0.48), (0.096, 0.54)]
    b.add(lathe([(0, 0.09)] + sk + [(0, 0.54)], seg=56, folds=13, famp=0.045, ftop=0.42), 'main')
    def rr(hh):
        for (r1, h1), (r2, h2) in zip(sk, sk[1:]):
            if h1 <= hh <= h2:
                return r1 + (r2 - r1) * (hh - h1) / (h2 - h1)
        return sk[-1][0]
    hs = [0.1 + 0.42 * i / 12 for i in range(13)]
    a0, a1 = 0.62 * math.pi, 2.38 * math.pi
    b.add(lathe([(rr(hh) + 0.01 + 0.012 * (0.52 - hh), hh) for hh in hs], seg=44, a0=a0, a1=a1, folds=9, famp=0.05, ftop=0.45), 'cape')
    for a in (a0, a1):
        b.add(sweep([((rr(hh) + 0.016) * math.cos(a), hh, (rr(hh) + 0.016) * math.sin(a)) for hh in hs], 0.007, seg=6), 'trim')
    b.add(ring((0, 0.105, 0), 0.268, 0.012, seg=64, tseg=6), 'trim')
    b.add(ring((0, 0.3, 0), 0.186, 0.006, seg=48, tseg=5), 'trim')
    b.add(lathe([(0, 0.52), (0.09, 0.52), (0.1, 0.56), (0.11, 0.63), (0.114, 0.68), (0.1, 0.71), (0.06, 0.73), (0, 0.735)], seg=40), 'main')
    b.add(ring((0, 0.54, 0), 0.093, 0.011, seg=40, tseg=6), 'trim')
    zz = []
    for i in range(9):
        hh = 0.555 + i * 0.013
        x = 0.022 * (1 if i % 2 else -1)
        zz.append((x, hh, 0.1 + 0.012 * (hh - 0.555) / 0.11 + 0.006))
    b.add(sweep(zz, 0.0035, seg=5), 'trim')
    b.add(ring((0, 0.708, 0), 0.098, 0.008, seg=40, tseg=5), 'trim')
    b.add(ring((0, 0.742, 0), 0.044, 0.007, seg=28, tseg=5), 'trim')
    b.add(sphere((0, 0.714, 0.07), 0.016, (1, 1.3, 0.7), u=12, v=8), 'gem')
    for s in (-1, 1):
        b.add(sphere((s * 0.112, 0.69, 0), 0.05, (1, 0.9, 1), u=18, v=12), 'main')
        b.add(ring((s * 0.12, 0.655, 0), 0.036, 0.006, seg=20, tseg=5), 'trim')
    b.add(tube((0, 0.72, 0), (0, 0.79, 0), 0.029, 0.027, seg=14), 'skin')
    b.add(sphere((0, 0.845, 0), 0.071, (1, 1.08, 1), u=24, v=16), 'skin')
    face(b, 0.845, 0.071, 0.071, ears=False, brows='hair', mouth=False)
    b.add(sphere((0, 0.817, 0.066), 0.012, (1.6, 0.6, 0.6), u=12, v=8), 'lips')
    b.add(lathe([(0, 0.935), (0.035, 0.93), (0.065, 0.905), (0.08, 0.87), (0.083, 0.84), (0.082, 0.835)], seg=36, off=(0, 0, -0.008)), 'hair')
    hairb = [(0.082, 0.86), (0.094, 0.8), (0.11, 0.72), (0.118, 0.66), (0.112, 0.62)]
    for s in (-1, 1):
        b.add(sweep([(s * 0.066, 0.87, 0.02), (s * 0.08, 0.81, 0.035), (s * 0.09, 0.75, 0.03), (s * 0.095, 0.71, 0.02)], [0.02, 0.022, 0.017, 0.006], seg=8), 'hair')
    b.add(sphere((0, 0.9, -0.07), 0.035, u=14, v=10), 'hair')
    b.add(lathe([(0.06, 0.915), (0.071, 0.915), (0.069, 0.962), (0.059, 0.962), (0.06, 0.915)], seg=36), 'trim')
    for i in range(5):
        a = i / 5 * 2 * math.pi + math.pi / 2
        x, z = math.cos(a) * 0.066, math.sin(a) * 0.066
        b.add(tube((x, 0.955, z), (x * 1.08, 1.0, z * 1.08), 0.011, 0.003, seg=8), 'trim')
        b.add(sphere((x * 1.08, 1.003, z * 1.08), 0.009, u=8, v=6), 'gem')
        b.add(sphere((math.cos(a + 0.63) * 0.07, 0.94, math.sin(a + 0.63) * 0.07), 0.007, u=8, v=6), 'gem')
    b.add(sphere((0, 0.938, 0.071), 0.014, (1, 1.2, 0.7), u=12, v=8), 'gem')
    # braço esquerdo segurando o vestido (estático)
    b.add(tube((-0.12, 0.68, 0), (-0.15, 0.58, 0.03), 0.03, 0.027, seg=12), 'main')
    b.add(tube((-0.15, 0.58, 0.03), (-0.1, 0.53, 0.1), 0.022, 0.02, seg=12), 'skin')
    b.add(ring((-0.15, 0.585, 0.03), 0.03, 0.006, seg=16, tseg=5), 'trim')
    hand(b, (-0.095, 0.525, 0.11), 0.022)
    b.build()
    qh = Part('q_hair', b, (0, 0.86, -0.02))
    qh.add_abs(lathe(hairb, seg=24, a0=1.05 * math.pi, a1=1.95 * math.pi, folds=11, famp=0.08, ftop=0.85, off=(0, 0, -0.01)), 'hair')
    qh.add_abs(sphere((0, 0.78, -0.065), 0.07, (1.2, 2.2, 0.55), u=18, v=12), 'hair')
    qh.build()
    arm = Part('q_arm', b, (0.12, 0.68, 0))
    arm.add(tube((0, 0, 0), (0.005, -0.1, 0), 0.03, 0.026, seg=12), 'main')
    arm.add(ring((0.005, -0.1, 0), 0.03, 0.007, seg=16, tseg=5), 'trim')
    arm.add(tube((0.005, -0.1, 0), (0.005, -0.18, 0), 0.021, 0.019, seg=12), 'skin')
    hand(arm, (0.005, -0.19, 0), 0.022)
    arm.add(tube((0.005, -0.18, 0), (0.005, -0.35, 0), 0.007, 0.006, seg=8), 'trim')
    arm.add(sphere((0.005, -0.37, 0), 0.026, u=16, v=12), 'gem')
    for k in range(4):
        a = k * math.pi / 2
        arm.add(tube((0.005, -0.352, 0), (0.005 + 0.02 * math.cos(a), -0.345, 0.02 * math.sin(a)), 0.005, 0.002, seg=6), 'trim')
    arm.build()
    empty('q_anchor', arm, (0.005, -0.37, 0))


# ===================== REI =====================
def build_king():
    R = root('piece_k')
    b = Part('k_body', R)
    base(b, 0.37)
    rp = [(0.27, 0.09), (0.272, 0.1), (0.25, 0.18), (0.226, 0.3), (0.2, 0.42), (0.18, 0.55), (0.165, 0.66), (0.15, 0.74), (0.09, 0.78)]
    b.add(lathe([(0, 0.09)] + rp + [(0, 0.79)], seg=56, folds=12, famp=0.045, ftop=0.5), 'main')
    def rr(hh):
        for (r1, h1), (r2, h2) in zip(rp, rp[1:]):
            if h1 <= hh <= h2:
                return r1 + (r2 - r1) * (hh - h1) / (h2 - h1)
        return rp[-1][0]
    b.add(ring((0, 0.12, 0), 0.266, 0.028, seg=64, tseg=10), 'fur')
    for i in range(16):
        a = i / 16 * 2 * math.pi
        b.add(sphere((math.cos(a) * 0.29, 0.125, math.sin(a) * 0.29), 0.008, (1, 1.6, 0.6), u=8, v=6, yaw=a), 'eye')
    hs = [0.13 + 0.6 * i / 12 for i in range(13)]
    b.add(sweep([(0, hh, rr(hh) + 0.004) for hh in hs], 0.024, seg=10, flat=0.45), 'fur')
    for hh in hs[1::2]:
        b.add(sphere((0, hh, rr(hh) + 0.017), 0.007, (0.7, 1.5, 0.5), u=8, v=6), 'eye')
    b.add(lathe([(0.205, 0.486), (0.212, 0.49), (0.212, 0.52), (0.204, 0.524), (0.205, 0.486)], seg=48), 'trim')
    for i in range(10):
        a = math.pi / 2 + (i - 4.5) * 0.28
        b.add(sphere((math.cos(a) * 0.214, 0.505, math.sin(a) * 0.214), 0.009, u=8, v=6), 'gem')
    # capa real com dobras
    capeh = [0.1 + 0.66 * i / 12 for i in range(13)]
    # gola de arminho
    b.add(lathe([(0.075, 0.8), (0.12, 0.79), (0.17, 0.755), (0.205, 0.7), (0.21, 0.68), (0.19, 0.675), (0.15, 0.72), (0.1, 0.765), (0.07, 0.785), (0.075, 0.8)], seg=48), 'fur')
    for i in range(14):
        a = i / 14 * 2 * math.pi
        b.add(sphere((math.cos(a) * 0.175, 0.745, math.sin(a) * 0.175), 0.007, (1, 1.5, 0.6), u=8, v=6, yaw=a), 'eye')
    b.add(tube((0, 0.78, 0), (0, 0.83, 0), 0.034, 0.032, seg=14), 'skin')
    b.add(sphere((0, 0.875, 0), 0.08, (1, 1.06, 1), u=26, v=16), 'skin')
    face(b, 0.88, 0.08, 0.08, eye_sp=0.03, brows='hair', mouth=False)
    b.add(sphere((0, 0.83, 0.045), 0.062, (1.05, 1.05, 0.7), u=20, v=12), 'hair')
    b.add(sweep([(0, 0.81, 0.06), (0, 0.77, 0.07), (0, 0.735, 0.072)], [0.04, 0.025, 0.0], seg=12), 'hair')
    for s in (-1, 1):
        b.add(sweep([(0, 0.857, 0.08), (s * 0.025, 0.86, 0.083), (s * 0.045, 0.852, 0.078), (s * 0.058, 0.838, 0.07)], [0.009, 0.009, 0.007, 0.002], seg=6), 'hair')
    b.add(lathe([(0.083, 0.9), (0.086, 0.87), (0.083, 0.83), (0.075, 0.8)], seg=20, a0=1.1 * math.pi, a1=1.9 * math.pi, off=(0, 0, -0.004)), 'hair')
    b.add(sphere((0, 0.905, -0.012), 0.083, (1, 0.8, 1), u=22, v=12), 'hair')
    # coroa
    b.add(lathe([(0.079, 0.945), (0.09, 0.945), (0.092, 1.0), (0.081, 1.0), (0.079, 0.945)], seg=48), 'trim')
    for i in range(10):
        a = i / 10 * 2 * math.pi
        b.add(sphere((math.cos(a) * 0.091, 0.972, math.sin(a) * 0.091), 0.01, (1, 1.2, 0.6), u=8, v=6, yaw=a + math.pi / 2), 'gem')
    for i in range(6):
        a = i / 6 * 2 * math.pi + math.pi / 2
        x, z = math.cos(a) * 0.086, math.sin(a) * 0.086
        b.add(tube((x, 0.995, z), (x * 1.06, 1.045, z * 1.06), 0.014, 0.004, seg=8), 'trim')
        b.add(sphere((x * 1.06, 1.05, z * 1.06), 0.011, u=10, v=8), 'trim')
    b.add(sphere((0, 1.0, 0), 0.076, (1, 0.75, 1), u=22, v=12), 'cape')
    b.add(ring((0, 1.0, 0), 0.082, 0.008, plane='xf', seg=24, tseg=6, a0=0, a1=math.pi), 'trim')
    b.add(ring((0, 1.0, 0), 0.082, 0.008, plane='side', seg=24, tseg=6, a0=0, a1=math.pi), 'trim')
    b.add(sphere((0, 1.09, 0), 0.02, u=14, v=10), 'trim')
    b.add(box((0, 1.135, 0), (0.016, 0.075, 0.016), bev=0.004), 'trim')
    b.add(box((0, 1.142, 0), (0.05, 0.016, 0.016), bev=0.004), 'trim')
    # braço esquerdo com o orbe (estático)
    b.add(sphere((-0.2, 0.7, 0), 0.042, u=14, v=10), 'main')
    b.add(tube((-0.2, 0.7, 0), (-0.22, 0.58, 0.06), 0.038, 0.034, seg=14), 'main')
    b.add(tube((-0.22, 0.58, 0.06), (-0.17, 0.54, 0.13), 0.032, 0.03, seg=14), 'main')
    b.add(ring((-0.2, 0.565, 0.085), 0.036, 0.012, plane='h', seg=18, tseg=6), 'fur')
    hand(b, (-0.165, 0.535, 0.14), 0.028)
    b.add(sphere((-0.16, 0.575, 0.15), 0.04, u=20, v=14), 'trim')
    b.add(ring((-0.16, 0.575, 0.15), 0.041, 0.005, plane='h', seg=24, tseg=5), 'gem')
    b.add(box((-0.16, 0.64, 0.15), (0.012, 0.05, 0.012), bev=0.003), 'trim')
    b.add(box((-0.16, 0.645, 0.15), (0.034, 0.012, 0.012), bev=0.003), 'trim')
    b.build()
    kcp = Part('k_cape', b, (0, 0.76, 0))
    kcp.add_abs(lathe([(rr(hh) + 0.02 + 0.06 * (0.76 - hh), hh) for hh in capeh], seg=40, a0=0.9 * math.pi, a1=2.1 * math.pi, folds=8, famp=0.07, ftop=0.62), 'cape')
    for a in (0.9 * math.pi, 2.1 * math.pi):
        kcp.add_abs(sweep([((rr(hh) + 0.024 + 0.06 * (0.76 - hh)) * math.cos(a), hh, (rr(hh) + 0.024 + 0.06 * (0.76 - hh)) * math.sin(a)) for hh in capeh], 0.008, seg=6), 'trim')
    kcp.build()
    arm = Part('k_arm', b, (0.2, 0.7, 0))
    arm.add(sphere((0, 0, 0), 0.042, u=14, v=10), 'main')
    arm.add(tube((0, 0, 0), (0, -0.13, 0), 0.038, 0.034, seg=14), 'main')
    arm.add(ring((0, -0.13, 0), 0.036, 0.013, seg=18, tseg=6), 'fur')
    arm.add(tube((0, -0.13, 0), (0, -0.2, 0), 0.03, 0.028, seg=12), 'main')
    hand(arm, (0, -0.215, 0), 0.028)
    arm.add(tube((0, -0.17, 0), (0, -0.42, 0), 0.013, seg=10), 'trim')
    arm.add(tube((0, -0.2, 0), (0, -0.26, 0), 0.016, seg=10), 'dark')
    arm.add(sphere((0, -0.165, 0), 0.016, u=10, v=8), 'trim')
    arm.add(sphere((0, -0.46, 0), 0.048, u=20, v=14), 'trim')
    for k in range(6):
        a = k / 6 * 2 * math.pi
        arm.add(box((math.cos(a) * 0.042, -0.46, math.sin(a) * 0.042), (0.012, 0.075, 0.032), bev=0.004, yaw=-a + math.pi / 2), 'steel')
    arm.add(tube((0, -0.5, 0), (0, -0.53, 0), 0.012, 0.0, seg=8), 'steel')
    arm.build()


for fn in (build_pawn, build_rook, build_knight, build_bishop, build_queen, build_king):
    fn()

# ---------- animações de espera (keyframes do Blender) ----------
scene.render.fps = 30
def idle(name, specs, period=60, n=12):
    o = bpy.data.objects[name]
    for (path, idx, amp, ph) in specs:
        base = getattr(o, path)[idx]
        for i in range(n + 1):
            getattr(o, path)[idx] = base + amp * math.sin(2 * math.pi * i / n + ph)
            o.keyframe_insert(data_path=path, index=idx, frame=1 + period * i / n)
        getattr(o, path)[idx] = base
    o.animation_data.action.name = 'idle_' + name
IDLE = {
    'p_body':   ([('scale', 2, 0.014, 0), ('rotation_euler', 1, 0.018, 1.0)], 64),
    'p_plume':  ([('rotation_euler', 0, 0.14, 0), ('rotation_euler', 2, 0.1, 1.2)], 40),
    'n_horse':  ([('scale', 2, 0.012, 0), ('rotation_euler', 0, 0.02, 0.6)], 56),
    'n_tail':   ([('rotation_euler', 2, 0.38, 0), ('rotation_euler', 0, 0.1, 1.4)], 44),
    'b_body':   ([('scale', 2, 0.012, 0)], 70),
    'b_cape':   ([('rotation_euler', 0, -0.05, 0), ('rotation_euler', 1, 0.03, 1.3)], 76),
    'q_body':   ([('scale', 2, 0.012, 0), ('rotation_euler', 1, 0.02, 0.8)], 66),
    'q_hair':   ([('rotation_euler', 0, -0.06, 0), ('rotation_euler', 1, 0.05, 1.1)], 58),
    'k_body':   ([('scale', 2, 0.012, 0)], 72),
    'k_cape':   ([('rotation_euler', 0, -0.045, 0), ('rotation_euler', 1, 0.03, 1.5)], 80),
}
for nm, (specs, per) in IDLE.items():
    idle(nm, specs, per)

bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_apply=True, export_yup=True,
                          export_texcoords=False, export_normals=True, export_materials='EXPORT',
                          export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
                          export_anim_single_armature=False, export_frame_range=False, use_active_scene=True)
tris = sum(len(o.data.loop_triangles) if (o.type == 'MESH' and (o.data.calc_loop_triangles() or True)) else 0 for o in bpy.data.objects)
print('OK', OUT, 'tris', tris)

# ---------- vitrine no viewport do Blender ----------
SAVE = os.path.join(os.path.dirname(OUT), 'pecas_xadrez.blend')
order = ['piece_p', 'piece_r', 'piece_n', 'piece_b', 'piece_q', 'piece_k']
for i, n in enumerate(order):
    bpy.data.objects[n].location = (-1.55 + i * 0.62, 0, 0)
scene.frame_start, scene.frame_end = 1, 81
try:
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                sp = area.spaces.active
                sp.shading.type = 'MATERIAL'
                r3 = sp.region_3d
                r3.view_location = (0, 0, 0.55)
                r3.view_distance = 3.6
                from mathutils import Euler
                r3.view_rotation = Euler((1.25, 0, 0)).to_quaternion()
                r3.view_perspective = 'PERSP'
except Exception as e:
    print('viewport', e)
try:
    bpy.ops.wm.save_as_mainfile(filepath=SAVE, copy=True)
except Exception as e:
    print('save', e)
try:
    if not bpy.context.screen.is_animation_playing:
        bpy.ops.screen.animation_play()
except Exception as e:
    print('play', e)
print('PRONTO', OUT, SAVE)
