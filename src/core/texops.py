from PIL.Image import Image
import PIL.Image
from PIL import ImageChops
import numpy as np
from .material import Material, MaterialMode

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

def normalize(img: Image, size: tuple[int, int]|None=None):
	''' Normalizes an input image to function with other operations. '''

	if img.mode == 'I':
		img_bytes = img.tobytes()

		arr = np.frombuffer( img_bytes, dtype=np.int32 ).astype( np.float32 )
		arr /= 256

		out_bytes = arr.astype( np.uint8 )
		img = PIL.Image.frombytes( 'L', img.size, out_bytes.tobytes() )

	elif img.mode == 'P':
		img = img.convert( 'RGB' )

	if size:
		img = img.resize(size)

	return img


def make_phong_exponent(mat: Material) -> Image:
	''' Generates an RGB phong exponent texture. '''

	# "The Phong exponent texture [...] red channel defines the Phong exponent value and the green for albedo tinting.
	# [...] albedo tinting is a "work in progress" feature and currently un-supported in the current shader in some branches."

	assert mat.roughness != None

	MAX_EXPONENT = 4 # $phongexponentfactor 8

	arr = np.asarray(mat.roughness.convert('F')) / 255
	arr = (0.8 / arr / MAX_EXPONENT)
	arr.clip(0, MAX_EXPONENT)

	exponent_r = PIL.Image.fromarray(arr * 255, 'F').convert('L')
	exponent_g = PIL.Image.new('L', mat.size, 255)
	exponent_b = PIL.Image.new('L', mat.size, 0)
	exponent = PIL.Image.merge('RGB', (exponent_r, exponent_g, exponent_b))

	return exponent


def make_phong_mask(mat: Material) -> Image:
	''' Generates a L phong mask texture. '''

	assert mat.roughness != None

	arr = np.asarray(mat.roughness.convert('F'))
	arr = (1 - arr)**5 * 2

	mask = PIL.Image.fromarray(arr, 'F').convert('L')
	if mat.ao: mask = ImageChops.multiply(mask, mat.ao)

	return mask


def make_envmask(mat: Material) -> Image:
	''' Creates an envmapmask texture from a material. '''

	metallic = np.asarray(mat.metallic.convert('F')) / 255
	roughness = np.asarray(mat.roughness.convert('F')) / 255
	tint = (metallic * 0.75 + 0.25) * (1 - roughness)**5

	return PIL.Image.fromarray(tint * 255, 'F').convert('L')


def make_basecolor(mat: Material) -> Image:
	''' Creates a basetexture from a material. '''

	assert mat.metallic != None
	assert mat.roughness != None
	assert mat.albedo != None

	# This was actually painful to write. Fix later.
	basetexture = ImageChops.multiply(
		ImageChops.invert(
			ImageChops.multiply(
				ImageChops.invert(
					mat.roughness
				),
				mat.metallic
			)
		).convert(mat.albedo.mode),
		mat.albedo)
	if mat.mode > 1 and mat.ao is not None: basetexture = ImageChops.multiply(basetexture, mat.ao.convert(mat.albedo.mode))

	if mat.mode == MaterialMode.PhongEnvmap:
		basetexture.putalpha(make_envmask(mat))

	return basetexture


def make_bumpmap(mat: Material) -> Image:
	''' Generates a RGBA bumpmap with embedded phong information when applicable. '''

	if mat.mode < 2: return mat.normal

	(r, g, b) = mat.normal.split()
	bump = PIL.Image.merge('RGB', (r, ImageChops.invert(g), b))
	bump.putalpha(make_phong_mask(mat))

	return bump


def make_mrao(mat: Material) -> Image:
	''' Generates a RGB MRAO texture. '''

	ao = mat.ao or PIL.Image.new('L', mat.size, 255)
	return PIL.Image.merge('RGB', (mat.metallic, mat.roughness, ao))