from PIL.Image import Image
import PIL.Image, PIL.ImageChops, PIL.ImageColor, PIL.ImageCms
import numpy as np
from material import Material, MaterialMode

'''
References:
- https://marmoset.co/posts/pbr-texture-conversion/
- https://cgobsession.com/complete-guide-to-texture-map-types/
- https://metzgar-research.com/games/conversion-between-specular-exponent-specular-roughness-and-specular-glossiness/
'''

def normalize(img: Image):
	''' Normalizes an input image to function with other operations. '''

	if img.mode == 'I':
		img_bytes = img.tobytes()

		arr = np.frombuffer( img_bytes, dtype=np.int32 ).astype( np.float32 )
		arr /= 256

		out_bytes = arr.astype( np.uint8 )
		img = PIL.Image.frombytes( 'L', img.size, out_bytes.tobytes() )

	elif img.mode == 'P':
		img = img.convert( 'RGB' )

	return img


def convert_albedo_specular(albedo: Image, metal: Image) -> Image:
	''' Converts albedo/metallic textures to albedo/specular textures. '''
	return (
		PIL.ImageChops.multiply(albedo, PIL.ImageChops.invert(metal)),
		PIL.Image.composite(PIL.Image.new('L', albedo.size, 0.04), albedo, metal)
	)


def convert_glossy(rough: Image) -> Image:
	''' Converts a roughness texture to a glossiness texture. '''
	return PIL.ImageChops.invert(rough)


def make_phong_exponent(mat: Material) -> (Image, Image):
	''' Generates phong exponent/intensity textures. '''

	assert mat.specular != None
	assert mat.glossy != None

	def glossy_to_exp(x: int):
		x /= 255
		x = 2 / ((1 - x)**2) - 2
		return int(x * 255)
	
	def specular_to_intensity(x: int):
		return x

	return (
		PIL.Image.eval(mat.glossy, glossy_to_exp),
		PIL.Image.eval(mat.specular, specular_to_intensity)
	)


def make_bump(mat: Material) -> Image:
	pass