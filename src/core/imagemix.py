from math import log2, log
import numpy as np
from PIL import Image, ImageChops
from PIL.Image import Image as ImType
from srctools.vtf import VTF


def validate( img: ImType ):
	
	# We have to do this to ensure that int32 images are converted correctly.
	if img.mode == 'I':
		img_bytes = img.tobytes()

		arr = np.frombuffer( img_bytes, dtype=np.int32 ).astype( np.float32 )
		arr /= 256

		out_bytes = arr.astype( np.uint8 )
		return Image.frombytes( 'L', img.size, out_bytes.tobytes() )
	
	if img.mode == 'P':
		return img.convert( 'RGB' )

	return img


def phong_exponent( roughness: ImType ) -> ImType:
	# This equation is based on nothing more than rough experimentation. Do not trust it!
	def eq( val ):
		val = max(val/255,0.001)
		return round( (1.9 - 2.85 * log(val)) / 35 * 255 )
	return Image.eval( roughness, eq )


def phong_intensity( roughness: ImType ) -> ImType:
	# This equation is based on nothing more than rough experimentation. Do not trust it!
	def eq( val ):
		val = max(val/255,0.001)
		return round( (-(3.1*(val-0.3))**3 + 15*val + 10*(1-val)**16) / 35 * 255 )
	return Image.eval( roughness, eq )


def make_basecolor( albedo: ImType, ao: ImType|None, emit: ImType|None, phong: ImType|None, burn_emit=False ) -> ImType:
	if emit and phong: raise Exception( 'Attempted to generate basetexture with both embedded emission and phong!' )

	out = albedo.copy()

	if ao:	out = ImageChops.multiply( albedo, ao.convert(albedo.mode) )
	if phong: out.putalpha( phong )
	if emit:
		if burn_emit: out = ImageChops.add( out, emit.convert('RGB') )
		out.putalpha( emit.convert('L') )

	return out


def make_bump( normal: ImType, alpha: ImType|None, invert_y=False ):
	if not ( alpha or invert_y ): return normal
	bump = normal.copy()

	if invert_y:
		x, y, z = bump.split()
		bump = Image.merge( 'RGB', (x, ImageChops.invert(y), z) )

	if alpha: bump.putalpha( alpha )

	return bump


def combine_mrao( metallic: ImType, roughness: ImType, ao: ImType ) -> ImType:
	return Image.merge( 'RGB', (metallic, roughness, ao) )


def convert_image( image: ImType, format: any ):
	vtf = VTF( image.width, image.height, fmt=format )
	vtf.mipmap_count = int(log2(min(image.size)) - 2)
	vtf.get().copy_from( image.convert('RGBA').tobytes() )
	return vtf