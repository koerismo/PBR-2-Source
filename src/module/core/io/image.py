import numpy as np
from numpy.typing import DTypeLike
from pathlib import Path
from typing import Literal
from abc import abstractmethod

class IOBackend():
	'''
	Represents an abstract I/O interface for saving and loading images to/from
	the user's filesystem. Only VTFs are exported from the application by default.
	'''

	@staticmethod
	@abstractmethod
	def save(image: 'Image', path: str|Path, version: int=5, compressed: bool=True) -> bool:
		...

	@staticmethod
	@abstractmethod
	def load(path: str|Path) -> 'Image':
		...

	@staticmethod
	@abstractmethod
	def resize(image: 'Image', dims: tuple[int, int]) -> 'Image':
		...

class Image():
	'''
	This class serves as a non-shit backend for vaguely-advanced image operations.
	It combines the functionality of PIL, while using numpy to skirt the
	limitations and general badness of the PIL API.
	'''


	backend: type[IOBackend] # static

	@staticmethod
	def set_backend(backend: type[IOBackend]):
		Image.backend = backend

	@staticmethod
	def load(path: str|Path) -> 'Image':
		return Image.backend.load(path)

	@staticmethod
	def blank(size: tuple[int, int], color: tuple[int|float, ...]=(1, 1, 1), dtype: DTypeLike='float32') -> 'Image':
		''' Creates a blank image by size, type, and color. '''
		data = np.ndarray((size[1], size[0], len(color)), dtype, order='C')
		data.fill(1)
		data *= color
		return Image(data)

	@staticmethod
	def merge(axes: tuple["Image", ...]) -> 'Image':
		''' Merges N images into one as color channels. '''
		for img in axes: assert img.channels == 1
		width, height = axes[0].size
		data = np.stack([img.data.reshape((height, width)) for img in axes])
		return Image(np.swapaxes(np.swapaxes(data, 0, 1), 1, 2))


	data: np.ndarray

	def __init__(self, src: np.ndarray) -> None:
		''' Creates a new image. src can be a filepath or a numpy array! '''
		if not isinstance(src, np.ndarray):
			raise NotImplementedError('Cannot construct generic image from non-ndarray. Use IO implementation!')

		self.data = src

		if self.channels == 1:
			self.data = self.data.reshape((self.size[1], self.size[0], 1))
	
	def resize(self, size: tuple[int, int]) -> 'Image':
		''' Resizes this image if necessary. '''
		if self.size == size: return self
		return Image.backend.resize(self, size)

	def convert(self, dtype: DTypeLike, clip=False) -> 'Image':
		''' Returns a copy of this image, converted to the specified datatype. '''
		obj_dtype = np.dtype(dtype)
		max_from: int = 1 if self.data.dtype.kind == 'f' else 2**(self.data.dtype.itemsize*8) - 1
		max_to: int   = 1 if obj_dtype.kind == 'f' else 2**(obj_dtype.itemsize*8) - 1
		new_data = self.data.copy('C') * (max_to / max_from)

		if clip:
			new_data = new_data.clip(0, max_to)

		return Image(new_data.astype(obj_dtype))

	def split(self) -> list["Image"]:
		''' Returns this image's data as a list of channels '''
		channels = np.swapaxes(np.swapaxes(self.data, 2, 1), 1, 0)
		return [Image(x) for x in channels]

	def normalize(self, mode: Literal['RGB', 'RGBA', 'L']) -> 'Image':
		s = self.split()
		if self.channels == 1:
			if mode == 'L': return self
			if mode == 'RGB': return Image.merge(( s[0], s[0], s[0] ))
			return Image.merge(( s[0], s[0], s[0], Image.blank(self.size, dtype=self.data.dtype, color=(1,)) ))
		if self.channels == 3:
			if mode == 'L': return self.split()[0]
			if mode == 'RGB': return self
			return Image.merge(( s[0], s[1], s[2], Image.blank(self.size, dtype=self.data.dtype, color=(1,)) ))
		if self.channels == 4:
			if mode == 'L': return self.split()[0]
			if mode == 'RGB': return Image.merge(tuple(self.split()[:3]))
			return self

		raise ValueError(f'Image has unrecognized number of channels ({self.channels})! Failed to convert to {mode}!')

	def grayscale(self):
		''' If required, grayscales the image. This might damage the original image! '''
		if self.channels == 1: return self
		assert self.channels == 3
		[r, g, b] = self.split()
		# https://en.wikipedia.org/wiki/Luma_(video)
		gray = r.mult(0.2126).add(g.mult(0.7152)).add(b.mult(0.0722))
		return gray

	def average(self):
		return np.average(self.data, (0, 1))

	def get_channel(self, channel: int) -> int:
		if channel >= self.channels: raise ValueError(f'Attempted to get channel {channel+1} of {self.channels}-channel image!')
		return self.data.swapaxes(0, 2)[channel]

	def set_channel(self, channel: int, image: "Image"):
		if channel >= self.channels: raise ValueError(f'Attempted to set channel {channel+1} of {self.channels}-channel image!')
		self.data.swapaxes(0, 2)[channel] = image.data

	def tobytes(self, format: DTypeLike) -> bytes:
		''' Converts this image to bytes. '''
		if self.data.dtype == format: return self.data.tobytes('C')
		return self.data.astype(format).tobytes('C')

	def save(self, path: str|Path, version: int=5, compressed: bool=True) -> bool:
		''' Saves this image to a file. Useful for debug. '''
		return Image.backend.save(self, path, version, compressed)

	def copy(self) -> "Image":
		''' Clones this image. '''
		return Image(self.data.copy())

	@property
	def size(self) -> tuple[int, int]:
		return (np.size(self.data, 1), np.size(self.data, 0))

	@property
	def channels(self) -> int:
		return 1 if len(self.data.shape) == 2 else np.size(self.data, 2)

	def mult(self, other: "Image|int|float"):
		''' Multiplies in-place, returning self. '''
		v: np.ndarray|int|float = other.data if isinstance(other, Image) else other
		self.data *= v
		return self

	def div(self, other: "Image|int|float"):
		''' Divides in-place, returning self. '''
		v = other.data if isinstance(other, Image) else other
		self.data /= v
		return self

	def pow(self, other: "Image|int|float"):
		''' Powers in-place, returning self. '''
		v = other.data if isinstance(other, Image) else other
		self.data **= other
		return self

	def add(self, other: "Image|int|float"):
		''' Adds in-place, returning self. '''
		v = other.data if isinstance(other, Image) else other
		self.data += v
		return self

	def sub(self, other: "Image|int|float"):
		''' Subtracts in-place, returning self. '''
		v = other.data if isinstance(other, Image) else other
		self.data -= v
		return self

	def invert(self):
		''' Inverts in-place, returning self. '''
		max_value: int = 1 if self.data.dtype.kind == 'f' else 2**(self.data.dtype.itemsize*8) - 1
		self.data = max_value - self.data
		return self

	def rot90(self, num: int=1):
		self.data = np.rot90(self.data, num, (0, 1))
		return self

	def flip_h(self):
		self.data = np.flip(self.data, 0)
		return self

	def flip_v(self):
		self.data = np.flip(self.data, 1)
		return self
