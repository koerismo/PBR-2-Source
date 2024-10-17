'''
This code is not meant to be pretty in any way shape or form.
Its only purpose is to be functional enough to convert stuff until the GUI is finished.
This code uses the Qt QImage API, though it can quite easily be replaced with imageio. See core/io/image.py
'''

if __name__ != '__main__':
	print( 'CLI cannot be run as module!' )
	exit(1)

from pathlib import Path
from argparse import ArgumentParser

# import core.io.vtf
from core.io.image import Image
from core.io.qtio import QtIOBackend
import core.convert as Convert
import core.material as Material
import core.vmt as Vmt
from tkinter.filedialog import asksaveasfilename

Image.set_backend(QtIOBackend)

parser = ArgumentParser( 'PBR-2-Source CLI', description='(BETA) A command line interface for PBR-2-Source.' )
parser.add_argument( 'source' )
parser.add_argument( '--target', dest='target', default=None, help='The output path. If none is provided, a file save prompt will be opened.' )
parser.add_argument( '--no-phong', action='store_true', help='Disable phong on the output material.' )
parser.add_argument( '--no-envmap', action='store_true', help='Disable envmaps on the output material.' )
parser.add_argument( '--only-vmt', action='store_true', help='Only generates the vmt.' )
parser.add_argument( '--only-vtf', action='store_true', help='Only generates the vtfs.' )
parser.add_argument( '--pbr', action='store_true', help='Convert to the Strata PBR format.' )
parser.add_argument( '--lmg', action='store_true', help='Convert to LightmappedGeneric (default is VertexLitGeneric).' )
parser.add_argument( '--mode', default='auto', choices=['auto','substance', 'ambientcg'], help='Overrides the material input mode.' )
args = parser.parse_args()

#
# DEFINE MODES
#

mode_substance = {
	'__normal__':	Material.NormalType.GL,
	'__name__':		'Substance',
	'albedo':		'_basecolor.png',
	'ao':			'_ambientocclusion.png',
	'emit':			'_emissive.png',
	'height':		'_height.png',
	'metallic':		'_metallic.png',
	'normal':		'_normal.png',
	'roughness':	'_roughness.png',
}

mode_substance_painter = {
	'__normal__':	Material.NormalType.DX,
	'__name__':		'Substance Painter',
	'albedo':		'_BaseColor.png',
	'ao':			'_AmbientOcclusion.png',
	'emit':			'_Emissive.png',
	'height':		'_Height.png',
	'metallic':		'_Metallic.png',
	'normal':		'_Normal.png',
	'roughness':	'_Roughness.png',
}

mode_ambientcg = {
	'__normal__':	Material.NormalType.DX,
	'__name__':		'AmbientCG',
	'albedo':		'_Color.png',
	'ao':			'_AmbientOcclusion.png',
	'emit':			'_Emission.png',
	'height':		'_Displacement.png',
	'metallic':		'_Metallic.png',
	'normal':		'_NormalDX.png',
	'roughness':	'_Roughness.png',
}

mode_textures_com = {
	'__normal__':	Material.NormalType.GL,
	'__name__':		'Textures.com',
	'albedo':		'_albedo.tif',
	'ao':			'_ao.tif',
	'emit':			'_emit.tif', # FIX
	'height':		'_height.tif',
	'metallic':		'_metallic.tif', # FIX
	'normal':		'_normal.tif',
	'roughness':	'_roughness.tif',
}

mode_polyhaven = {
	'__normal__':	Material.NormalType.GL,
	'__name__':		'PolyHaven',
	'albedo':		'_diff_1k.png',
	'ao':			'_ao_1k.png',
	'emit':			'_emit_1k.png',
	'height':		'_disp_1k.png',
	'metallic':		'_metal_1k.png',
	'normal':		'_nor_gl_1k.png',
	'roughness':	'_rough_1k.png',
}

modes = [mode_substance, mode_substance_painter, mode_ambientcg, mode_textures_com,mode_polyhaven]
mode_ids = { 'substance': 0, 'substance_painter': 1, 'ambientcg': 2, 'textures.com': 3, 'polyhaven': 4 }

#
# DETERMINE MATERIAL SOURCE LOCATION
#

path_src = Path( args.source )
path_src_name = path_src.name
mat_path = Path( '/' )

if not path_src.exists():
	print('Source path does not exist!')
	exit(1)

if path_src.is_dir():
	print('Directory sources have not yet been implemented!')
	exit(1)

#
# DETERMINE INPUT MODE
#

mat_mode = None if args.mode == 'auto' else modes[mode_ids.get(args.mode, 0)]
if mat_mode is None:
	file_name = path_src.name
	for mode in modes:
		if not file_name.endswith(mode['albedo']): continue
		print(f'Found {mode["__name__"]} material!')
		mat_mode = mode

if mat_mode is None:
	print('Could not match source file to texture input mode!')
	exit(1)

path_src_name = path_src_name[:-len(mat_mode['albedo'])]

#
# READ FILES
#

files = {}
for k, v in mat_mode.items():
	if k.startswith('__'): continue
	p: Path = path_src.parent / (path_src_name + v)
	if p.exists():
		files[k] = p
		print(p, k)

if len(({'albedo','roughness','normal'}).difference(set(files))):
	print( 'Albedo/normal/roughness textures must be present!' )
	exit(1)

for k, v in mat_mode.items():
	if k.startswith('__'): continue
	if k not in files: files[k] = None
	else:
		files[k] = Image.load(str(files[k]))
		# files[k] = Image( files[k] )


raw_path_target = args.target or asksaveasfilename(title='Save VMT', filetypes=[('Valve Material Type', '*.vmt')])
if not len(raw_path_target):
	print('Operation cancelled by user.')
	exit(0)

path_target = Path( raw_path_target ).with_suffix('.vmt')

#
# PROCESS AND CONVERT MATERIAL
#

path_target_name = path_target.name[:-4]
path_target_dir = path_target.parent
material_path = path_target_name

material_mode = Material.MaterialMode.PhongEnvmap
if args.lmg: material_mode = Material.MaterialMode.Envmap

mat = Convert.from_images(files, material_path, material_mode, Material.GameTarget.V2023)
mat.normalType = mat_mode['__normal__']
images = Convert.export(mat)
vtf_version = Material.GameTarget.vtf_version(mat.target)

for tex in images:
	tex_path = path_target_dir / (path_target_name + tex.name + '.vtf')
	print(f'Saving file {tex_path} ...')
	tex.image.save(tex_path, version=vtf_version)

	vmt = Vmt.make_vmt(mat)
	with open( path_target, 'w') as file:
		file.writelines(vmt)

# with open( path_target.parent / (matname+'.vmt'), 'w' ) as file:
# 	file.write( vmt )
