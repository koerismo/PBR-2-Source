import logging
log = logging.Logger( 'ImageCore', logging.DEBUG )

from pathlib import PurePath
from PIL.Image import Image as ImType
from PIL import Image
from srctools.vtf import ImageFormats as VIF
from . import vmtgen, imagemix

def compile_textures(
		path: PurePath,

		albedo: ImType,
		ao: ImType|None,
		roughness: ImType,
		metallic: ImType|None,
		normal: ImType,
		emit: ImType|None,
		height: ImType|None,

		model: bool=True,
		pbr: bool=False,

		envmap: str='env_cubemap',
		phong: bool=False,
		parallax: bool=False,
		alpha: int=0,

		burn_emit: bool=False,
		invert_y: bool=False,

		resize: None|tuple[int,int]=None,
		resize_albedo: None|tuple[int,int]=None,
		compress: bool=False,
		compress_albedo: bool=False,

	) -> dict[str,ImType]:

	# Type verification to prevent badness later on
	assert isinstance( path, PurePath )
	assert isinstance( albedo, ImType )
	assert isinstance( roughness, ImType )
	if metallic: assert isinstance( metallic, ImType )
	assert isinstance( normal, ImType )
	if ao: assert isinstance( ao, ImType )
	if emit: assert isinstance( emit, ImType )
	if height: assert isinstance( height, ImType )

	if not path.suffix: raise Exception( 'Path provided must reference a vmt file!' )

	log.debug( 'Generating vmt...' )

	vmt, info = vmtgen.generate_vmt(
		path,
		model,
		pbr,
		alpha,
		emit != None,
		envmap,
		phong,
		parallax )

	albedo_size	= resize_albedo or albedo.size
	other_size	= resize or albedo.size
	phong_size  = albedo_size if info['phong_embedded_albedo'] else other_size

	log.debug( 'Preparing images...' )

	# Prepare albedo and albedo parts
	albedo		= imagemix.validate(albedo).resize( albedo_size ).convert( 'RGB' )
	ao			= imagemix.validate(ao).resize( other_size if pbr else albedo_size ).convert( 'L' ) if ao else None

	# Resize other maps to appropriate sizes
	roughness	= imagemix.validate(roughness).resize( phong_size ).convert( 'L' )
	metallic	= imagemix.validate(metallic).resize( phong_size ).convert( 'L' ) if metallic else Image.new('L', phong_size, 0)
	normal		= imagemix.validate(normal).resize( other_size ).convert( 'RGB' )
	height		= imagemix.validate(height).resize( other_size ).convert( 'L' ) if height else None

	p_exponent	= imagemix.phong_exponent( roughness ) if phong and not pbr else None
	p_intensity = imagemix.phong_intensity( roughness ) if phong and not pbr else None

	# Emit can either be an RGB or L texture. Depending on this, it is treated as emission or emission intensity.
	emit		= imagemix.validate(emit).resize( albedo_size if info['emit_embedded_albedo'] else other_size ) if emit else None
	mrao		= imagemix.combine_mrao( metallic, roughness, ao ) if pbr else None
	bump		= imagemix.make_bump( normal, height if info['height_embedded_normal'] else p_intensity if info['phong_embedded_normal'] else None, invert_y=invert_y )

	basecolor	= imagemix.make_basecolor(
		albedo, ao if not pbr else None,
		emit if info['emit_embedded_albedo'] else None,
		p_intensity if info['phong_embedded_albedo'] else None, burn_emit=burn_emit )

	if info['phong_embedded_albedo']: p_intensity = None
	if info['emit_embedded_albedo']: emit = None

	# Export everything

	formats_uncompressed = {
		'L':	VIF.I8,
		'RGB':	VIF.RGB888,
		'RGBA':	VIF.RGBA8888,
	}

	formats_compressed = {
		'L':	VIF.I8,
		'RGB':	VIF.DXT1,
		'RGBA':	VIF.DXT5,
	}

	images = {
		'albedo':		basecolor,
		'mrao':			mrao,
		'bump':			bump,
		'emit':			emit,
		'exp':			p_exponent,
	}

	mat_name = path.name[:-len(path.suffix)]
	images_compiled = {}

	for (name, image) in images.items():
		if image == None:
			log.debug( 'Skipping', name )
			continue

		is_compressed = compress_albedo if name == 'basetexture' else compress
		target_format = formats_compressed[image.mode] if is_compressed else formats_uncompressed[image.mode]

		log.debug( 'Exporting', name, 'with target format', target_format )
		images_compiled[mat_name+'_'+name] = imagemix.convert_image( image, target_format )

	return vmt, images_compiled