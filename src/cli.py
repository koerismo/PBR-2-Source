'''
This code is not meant to be pretty in any way shape or form.
Its only purpose is to be functional enough to convert stuff until the GUI is finished.
'''

if __name__ != '__main__':
	print( 'CLI cannot be run as module!' )
	exit(1)


from re import M
import core as imagecore, os
from pathlib import Path
from argparse import ArgumentParser
from PIL import Image


parser = ArgumentParser( 'PBR-2-Source CLI', description='(BETA) A command line interface for PBR-2-Source.' )
parser.add_argument( 'source' )
parser.add_argument( '--target', dest='target', default=None, help='The output directory for materials. If none is provided, it will default to the source directory.' )
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

presets = {
	'default': preset_default,
	'pbr-brush': preset_pbr_brush,
	'pbr-model': preset_pbr_model,
	'brush': preset_brush,
	'model': preset_model,
}

modes = {
	'substance': mode_substance,
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

if len(({'albedo','metallic','rough','normal'}).difference(set(files))):
	print( 'Albedo/normal/roughness/metallic texture must be present!' )
	exit(1)

for k, v in curmode.items():
	if k not in files: files[k] = None
	else:
		img = Image.open( path_src.parent / (matname+v) )
		img.load()
		files[k] = img

vmt, images = imagecore.compile_textures(
	mat_path / (matname+'.vmt'),
	model=curpreset['model'],
	pbr=curpreset['pbr'],
	envmap='env_cubemap',
	phong=curpreset['phong'],
	parallax=curpreset['parallax'],
	alpha=(img.mode == 'RGBA' or img.mode == 'LA' or img.mode == 'PA'),

	resize=curpreset['resize'],
	resize_albedo=curpreset['resize_albedo'],

	compress=False,
	compress_albedo=False,

	burn_emit=False,
	invert_y=False,
	
	albedo=files['albedo'],
	ao=files['ao'],
	roughness=files['rough'],
	metallic=files['metallic'],
	normal=files['normal'],
	emit=files['emit'],
	height=files['height'] )

for path, img in images.items():
	with open( path_target.parent / (path+'.vtf'), 'wb' ) as file:
		img.save( file )

with open( path_target.parent / (matname+'.vmt'), 'w' ) as file:
	file.write( vmt )
