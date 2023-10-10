import imageio.v3 as imageio
import numpy as np
from numpy.typing import DTypeLike
from pathlib import Path
import PIL.Image
import vtf

'''
This class serves as a non-shit backend for vaguely-advanced image operations.
It combines the functionality of PIL, while using numpy to skirt the
limitations and general badness of the PIL API.
'''

class Image():
	src: np.ndarray

	def __init__(self, src: np.ndarray|str) -> None:
		if isinstance(src, str):
			self.src = imageio.imread(Path(src))
		else:
			self.src = src

	def resize(self, size: tuple[int, int], sampler: PIL.Image.Resampling|None=None) -> "Image":
		''' Resizes this image with the PIL backend. '''
		pimg = PIL.Image.fromarray(self.src)
		pimg = pimg.resize(size, sampler)
		return Image(np.asarray(pimg).copy())

	def convert(self, dtype: DTypeLike) -> "Image":
		''' Converts this image's datatype. '''
		return Image(self.src.astype(dtype, copy=True))

	def tobytes(self, format: DTypeLike) -> bytes:
		''' Converts this image to bytes. '''
		return self.src.astype(format).tobytes('C')

	def save(self, path: str) -> None:
		''' Saves this image to a file. Useful for debug. '''
		try:
			imageio.imwrite(Path(path), self.src)
		except TypeError as e:
			# Wrap the error message, since the default one is totally useless.
			_, _, ext = path.rpartition('.')
			raise TypeError(f'Invalid datatype - attempted to save {self.src.dtype} data to a ".{ext}" file! '+str(e))

	def copy(self):
		''' Clones this image. '''
		return Image(self.src.copy())

	@property
	def size(self) -> tuple[int, int]:
		return (np.size(self.src, 1), np.size(self.src, 0))

	def __mul__(self, other: "Image|float|int"):
		if isinstance(other, Image): return Image( self.src * other.src )
		return Image( self.src * other )

	def __div__(self, other: "Image|float|int"):
		if isinstance(other, Image): return Image( self.src / other.src )
		return Image( self.src / other )

	def __pow__(self, other: "Image|float|int"):
		if isinstance(other, Image): return Image( self.src ** other.src )
		return Image( self.src ** other )

	def __add__(self, other: "Image|float|int"):
		if isinstance(other, Image): return Image( self.src + other.src )
		return Image( self.src + other )

	def __sub__(self, other: "Image|float|int"):
		if isinstance(other, Image): return Image( self.src - other.src )
		return Image( self.src - other )
