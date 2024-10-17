from typing import Any, Dict

import imageio.v3 as imageio
from pathlib import Path

from imageio.core.request import Request
from imageio.core.format import Array
from imageio.typing import ArrayLike
import imageio.core as imcore
import imageio.plugins as implugins

from .image import Image, IOBackend
import numpy as np
import srctools.vtf as vtf
from srctools.vtf import VTF, ImageFormats

class ImIOBackend(IOBackend):
	@staticmethod
	def load(path: str|Path) -> Image:
		src = imageio.imread(Path(path) if isinstance(path, str) else path)
		return Image(src)

	@staticmethod
	def save(image: Image, path: str | Path, version: int=5, compressed: bool=True) -> None:
		try:
			imageio.imwrite(path if isinstance(path, Path) else Path(path), image.data, version=version, compressed=compressed)
		except TypeError as e:
			# Wrap the error message, since the default one is totally useless.
			_, _, ext = str(path).rpartition('.')
			raise TypeError(f'Invalid datatype - attempted to save {image.data.dtype} data to a ".{ext}" file! '+str(e))

	@staticmethod
	def resize(image: Image, dims: tuple[int, int]) -> Image:
		raise NotImplementedError('The ImageIO backend cannot resize images!')

class VtfFormat(imcore.format.Format):

	def __init__(self, name: str, description: str, extensions: str|list|tuple|None, modes: str) -> None:
		super().__init__(name, description, extensions, modes)

	def _can_read(self, request: Request) -> bool:
		return request.extension in self.extensions

	def _can_write(self, request: Request) -> bool:
		return request.extension in self.extensions


	class Writer(imcore.format.Format.Writer):
		version: int
		compressed: bool

		def _open(self, **kwargs) -> None:
			self.file = self.request.get_file()
			self.vtf = None
			self.version = kwargs.get('version', 5)
			self.compressed = kwargs.get('compressed', True)

		def _close(self) -> None:
			pass

		def _append_data(self, im: ArrayLike, meta: Dict[str, Any]) -> None:
			if not isinstance(im, np.ndarray):
				raise TypeError(f"Vtf writer expected nparray, but got {type(im)} instead!")

			height, width, bands = im.shape

			format = None
			target_format = None


			flags = vtf.VTFFlags.EMPTY
			max_value = 255
			match (bands, im.dtype):
				case (1, 'uint8'):
					format = ImageFormats.I8
				case (3, 'uint8'):
					if self.compressed:	target_format = ImageFormats.DXT1
					format = ImageFormats.RGB888
				case (4, 'uint8'):
					if self.compressed:	target_format = ImageFormats.DXT5
					format = ImageFormats.RGBA8888
					flags |= vtf.VTFFlags.EIGHTBITALPHA
				case (4, 'uint16'):
					format = ImageFormats.RGBA16161616
					flags |= vtf.VTFFlags.EIGHTBITALPHA
					max_value = 0xffff
				case (4, 'float16'):
					format = ImageFormats.RGBA16161616F
					flags |= vtf.VTFFlags.EIGHTBITALPHA
					max_value = 1.0

			if format is None:
				raise TypeError(f"Could not match format {im.dtype}x{bands}!")
			
			if target_format is None:
				target_format = format

			self.vtf = vtf.VTF(width, height, (7, self.version), fmt=target_format, flags=flags)
			self.vtf.get().copy_from(im.tobytes('C'), format)
			
			# Use color for reflectivity
			average = np.average(im, (0, 1))
			if bands >= 3:
				self.vtf.reflectivity.x = average[0] / max_value
				self.vtf.reflectivity.y = average[1] / max_value
				self.vtf.reflectivity.z = average[2] / max_value
			else:
				amount = average[0] / max_value
				self.vtf.reflectivity.x = amount
				self.vtf.reflectivity.y = amount
				self.vtf.reflectivity.z = amount

			# Save
			self.vtf.save(self.file)

	class Reader(imcore.format.Format.Reader):
		vtf: VTF

		def _open(self, **kwargs) -> None:
			self.vtf = VTF.read(self.request.get_file())

		def _get_data(self, index: int):
			frame = self.vtf.get()
			frame.load()
			data = np.array(frame._data).reshape((frame.width, frame.height, 4))
			return (data, {})
		
		def _get_meta_data(self, index: int) -> Dict[str, Any]:
			return {}
		
		def _get_length(self) -> int:
			return 1

		def _close(self) -> None:
			return super()._close()


implugins.formats.add_format(VtfFormat("VTF", "Implements the Valve Texture Format", ["vtf"], "i"))