'''
This code is not meant to be pretty in any way shape or form.
Its only purpose is to be functional enough to convert stuff until the GUI is finished.
'''

if __name__ != '__main__':
	print( 'CLI cannot be run as module!' )
	exit(1)

from pathlib import Path
from argparse import ArgumentParser
from .core.io.image import Image

import core.convert as Convert
import core.material as Material
import core.vmt as Vmt

from srctools.vtf import VTF, VTFFlags


parser = ArgumentParser( 'PBR-2-Source CLI', description='(BETA) A command line interface for PBR-2-Source.' )
parser.add_argument( 'source' )
parser.add_argument( '--target', dest='target', default=None, help='The output path. If none is provided, it will default to the source file names.' )
parser.add_argument( '--mode', default='substance', help='What patterns the program should use to search for the texture files.', dest='mode' )
parser.add_argument( '--preset', default='default', help='What preset the program should use to determine the output parameters.', dest='preset' )
# parser.add_argument( '--onlyvmt', action='store_true', help='Only generates the vmt.' )
# parser.add_argument( '--onlytex', action='store_true', help='Only generates the vtfs.' )
args = parser.parse_args()

preset_default = {
	'model':		True,
	'pbr':			False,
	'phong':		False,
	'alpha':		0,
	'envmap':		'env_cubemap',
	'parallax':		False,
	'burn_emit':	False,
	'invert_y':		False,
	'resize':			None,
	'resize_albedo':	None,
	'compress':			False,
	'compress_albedo':	False,
}

preset_pbr_model = {
	'model':		True,
	'pbr':			True,
}

preset_pbr_brush = {
	'model':		False,
	'pbr':			True,
	'resize_albedo':	(512,512),
}

preset_model = {
	'model':		True,
	'pbr':			False,
	'phong':		True,
}

preset_brush = {
	'model':		False,
	'pbr':			False,
	'phong':		True,
	'resize_albedo':	(512,512),
}

mode_substance = {
	'albedo':	'_basecolor.png',
	'ao':		'_ambientocclusion.png',
	'emit':		'_emissive.png',
	'height':	'_height.png',
	'metallic':	'_metallic.png',
	'normal':	'_normal.png',
	'rough':	'_roughness.png',
}

mode_ambientcg = {
	'albedo':		'_Color.png',
	'ao':			'_AmbientOcclusion.png', # FIX
	'emit':			'_Emission.png', # FIX
	'height':		'_Displacement.png',
	'metallic':		'_Metallic.png', # FIX
	'normal':		'_NormalDX.png',
	'roughness':	'_Roughness.png',
}

presets = {
	'default': preset_default,
	'pbr-brush': preset_pbr_brush,
	'pbr-model': preset_pbr_model,
	'brush': preset_brush,
	'model': preset_model,
}

modes = {
	'substance': mode_substance,
	'ambientcg': mode_ambientcg,
}

path_src = Path( args.source )
path_target = Path( args.target ) if args.target else path_src
mat_path = Path( '/' )
if not path_src.is_file() or not path_src.exists():
	print( 'Source file must be defined!' )
	exit(1)

curmode = modes[args.mode]
curpreset = preset_default
curpreset.update(presets[args.preset])

matname = path_src.name
for k, v in curmode.items():
	if matname.endswith( v ):
		matname = matname[:-len(v)]
		break

files = {}
for k, v in curmode.items():
	p: Path = path_src.parent / (matname+v)
	if p.exists(): files[k] = p

if len(({'albedo','roughness','normal'}).difference(set(files))):
	print( 'Albedo/normal/roughness textures must be present!' )
	exit(1)

for k, v in curmode.items():
	if k not in files: files[k] = None
	else:
		files[k] = Image( path_src.parent / (matname+v) )


def make_vtf(img: Image):
	width, height = img.size
	v = VTF(width, height)
	v.get().copy_from(img.tobytes('uint8'))
	return v

mat = Convert.from_images(files, "testy", Material.MaterialMode.PhongEnvmap)
images = Convert.export(mat)


for tex in images:
	# tex.image.save("test/amogus"+tex.name+".png", optimize=False)
	with open( 'test/tiles' + (tex.name+'.vtf'), 'wb' ) as file:
		make_vtf(tex.image).save( file )

	vmt = Vmt.make_vmt(mat)
	with open( 'test/tiles.vmt', 'w') as file:
		file.writelines(vmt.export())

# with open( path_target.parent / (matname+'.vmt'), 'w' ) as file:
# 	file.write( vmt )
