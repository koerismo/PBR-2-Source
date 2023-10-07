from PIL.Image import Image
import PIL.Image, PIL.ImageChops, PIL.ImageColor, PIL.ImageCms
import numpy as np
from srctools.vtf import VTF
from .material import Material, MaterialMode

'''
References:
- https://marmoset.co/posts/pbr-texture-conversion/
- https://cgobsession.com/complete-guide-to-texture-map-types/
'''

'''
	basetexture   = (1 - ((1-roughness) * metallic)) * albedo
	envmaptint    = (metallic * 0.75 + 0.25) * ((1-roughness)**5)
	phongexponent = (0.2 / (roughness**3)) * 4
	phongmask     = ((1-roughness)**4.8) * 2
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


# def convert_albedo_metallic(albedo: Image, specular: Image) -> tuple[Image, Image]:
# 	''' Converts albedo/specular textures to albedo/metallic textures. '''
# 	return (
# 		PIL.ImageChops.multiply(albedo, PIL.ImageChops.invert(specular)),
# 		PIL.Image.composite(PIL.Image.new('L', albedo.size, 0.04), albedo, specular)
# 	)


# def convert_glossy(rough: Image) -> Image:
# 	''' Converts a roughness texture to a glossiness texture. '''
# 	return PIL.ImageChops.invert(rough)


def make_phong(mat: Material) -> tuple[Image, Image]:
	''' Generates phong exponent/intensity textures. '''

	# "The Phong exponent texture [...] red channel defines the Phong exponent value and the green for albedo tinting.
	# [...] albedo tinting is a "work in progress" feature and currently un-supported in the current shader in some branches."

	assert mat.metallic != None
	assert mat.roughness != None

	def glossy_to_exp(x: int):
		f = x / 255
		f = 2 / ((1 - f)**2) - 2
		return int(f * 255)

	def specular_to_intensity(x: int):
		return x

	return (
		PIL.Image.eval(mat.glossy, glossy_to_exp),
		PIL.Image.eval(mat.specular, specular_to_intensity)
	)


def make_basecolor(mat: Material) -> Image:
	''' Creates a basetexture from a material. '''
	if mat.mode < 2 and mat.ao is not None: return PIL.ImageChops.multiply(mat.albedo, mat.ao)
	return mat.albedo

