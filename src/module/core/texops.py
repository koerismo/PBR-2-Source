from typing import Literal
from .io.image import Image
from .material import Material, MaterialMode, NormalType

'''
References:
- https://marmoset.co/posts/pbr-texture-conversion/
- https://cgobsession.com/complete-guide-to-texture-map-types/
'''

'''
	basetexture   = (1 - ((1-roughness) * metallic)) * albedo
	envmapmask    = (metallic * 0.75 + 0.25) * ((1-roughness)^5)
	phongexponent = (0.8 / (roughness^3)) # it is assumed that $phongexponent = 1
	phongmask     = ((1-roughness)^5.4) * 2
'''

def normalize(img: Image, size: tuple[int, int]|None=None, mode: Literal['L', 'RGB', 'RGBA']|None=None):
	''' Normalizes an input image to function with other operations. '''

	# All of this code is necessary to ensure that PIL imports work,
	# but I do not yet know if the same issues apply to imageio.

	# if img.mode == 'I':
	# 	img_bytes = img.tobytes()

	# 	arr = np.frombuffer( img_bytes, dtype=np.int32 ).astype( np.float32 )
	# 	arr /= 256

	# 	out_bytes = arr.astype( np.uint8 )
	# 	img = PIL.Image.frombytes( 'L', img.size, out_bytes.tobytes() )

	# elif img.mode == 'P':
	# 	img = img.convert( 'RGB' )

	if size:
		img = img.resize(size)

	if mode:
		img = img.convert('float32').normalize(mode)

	return img


def make_phong_exponent(mat: Material) -> Image:
	''' Generates an RGB phong exponent texture. '''

	# "The Phong exponent texture [...] red channel defines the Phong exponent value and the green for albedo tinting.
	# [...] albedo tinting is a "work in progress" feature and currently un-supported in the current shader in some branches."

	assert mat.roughness != None

	MAX_EXPONENT = 32 # $phongexponentfactor 32
	exponent_r = mat.roughness.copy().pow(-3).mult(0.8).div(MAX_EXPONENT)
	exponent_g = Image.blank(mat.size, color=(1,))
	exponent_b = Image.blank(mat.size, color=(0,))
	exponent = Image.merge((exponent_r, exponent_g, exponent_b))

	return exponent


def make_phong_mask(mat: Material) -> Image:
	''' Generates a L phong mask texture. '''

	assert mat.roughness != None

	mask = mat.roughness.copy().invert().pow(5).mult(2)
	if mat.ao: mask.mult(mat.ao)

	return mask


def make_envmask(mat: Material) -> Image:
	''' Creates an envmapmask texture from a material. '''

	assert mat.metallic != None
	assert mat.roughness != None

	mask1 = mat.metallic.copy().mult(0.75).add(0.25)
	mask2 = mat.roughness.copy().invert().pow(5)

	return mask1.mult(mask2)


def make_basecolor(mat: Material) -> Image:
	''' Creates a basetexture from a material. '''

	assert mat.metallic != None
	assert mat.roughness != None
	assert mat.albedo != None

	mask = mat.roughness.copy().invert()
	mask.mult(mat.metallic)
	mask.invert()

	if not MaterialMode.is_pbr(mat.mode) and mat.ao is not None:
		ao_blend = 0.75
		ao = mat.ao.copy().mult(ao_blend).add(1 - ao_blend)
		mask.mult(ao)

	basetexture = mat.albedo.copy().mult(mask)

	# Envmask as basetexture alpha
	if MaterialMode.embed_envmap(mat.mode):
		rgba = basetexture.split()
		envmask = make_envmask(mat)
		basetexture = Image.merge((rgba[0], rgba[1], rgba[2], envmask))

	# Emission as basetexture alpha
	# TODO: Burn emission color into image when using VLG/LMG
	if MaterialMode.embed_selfillum(mat.mode):
		assert mat.emit != None, 'An emissive texture is required for this mode!'
		rgba = basetexture.split()
		emitmask = mat.emit.copy().grayscale()
		basetexture = Image.merge((rgba[0], rgba[1], rgba[2], emitmask))

	return basetexture


def make_bumpmap(mat: Material) -> Image:
	''' Generates a RGB/RGBA bumpmap with embedded phong information when applicable. '''

	if mat.mode < 2: return mat.normal

	(r, g, b) = mat.normal.split()
	if mat.normal_type == NormalType.GL: g.invert()

	if MaterialMode.has_phong(mat.mode):
		a = make_phong_mask(mat)
		return Image.merge((r, g, b, a))
	
	if MaterialMode.is_pbr(mat.mode) and mat.height:
		return Image.merge((r, g, b, mat.height))

	return Image.merge((r, g, b))


def make_mrao(mat: Material) -> Image:
	''' Generates a RGB MRAO texture. '''

	ao = mat.ao or Image.blank(mat.size, color=(1,))
	return Image.merge((mat.metallic, mat.roughness, ao))
