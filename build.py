"""Monta o index.html final: embute os modelos GLB (feitos no Blender) dentro do código-fonte."""
import base64, os
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, 'src', 'index.src.html'), encoding='utf-8').read()
b64 = lambda p: base64.b64encode(open(os.path.join(HERE, 'assets', p), 'rb').read()).decode()
out = src.replace('__GLB_BASE64__', b64('pieces.glb')).replace('__SCENES_BASE64__', b64('scenes.glb'))
open(os.path.join(HERE, 'index.html'), 'w', encoding='utf-8').write(out)
print('index.html gerado:', len(out) // 1024, 'KB')
