from typing import Any, Dict
from imageio.core.request import Request
from imageio.typing import ArrayLike
import imageio.core as imcore
import imageio.plugins as implugins

import numpy as np
import srctools.vtf as vtf


class VtfFormat(imcore.format.Format):

	def __init__(self, name: str, description: str, extensions: str|list|tuple|None, modes: str) -> None:
		super().__init__(name, description, extensions, modes)

	def _can_read(self, request: Request) -> bool:
		return request.extension in self.extensions

	def _can_write(self, request: Request) -> bool:
		return request.extension in self.extensions


	class Writer(imcore.format.Format.Writer):

		def _open(self, **kwargs) -> None:
			self.file = self.request.get_file()
			self.vtf = None

		def _close(self) -> None:
			pass

		def _append_data(self, im: ArrayLike, meta: Dict[str, Any]) -> None:
			if not isinstance(im, np.ndarray):
				raise TypeError(f"Vtf writer expected nparray, but got {type(im)} instead!")

			height, width, bands = im.shape

			format = None
			flags = vtf.VTFFlags.EMPTY
			match (bands, im.dtype):
				case (1, 'uint8'): format = vtf.ImageFormats.I8
				case (3, 'uint8'): format = vtf.ImageFormats.RGB888
				case (4, 'uint8'):
					format = vtf.ImageFormats.RGBA8888
					flags |= vtf.VTFFlags.EIGHTBITALPHA
				case (4, 'uint16'):
					format = vtf.ImageFormats.RGBA16161616
					flags |= vtf.VTFFlags.EIGHTBITALPHA
				case (4, 'float16'):
					format = vtf.ImageFormats.RGBA16161616F
					flags |= vtf.VTFFlags.EIGHTBITALPHA

			if format is None:
				raise TypeError(f"Could not match format {im.dtype}x{bands}!")

			self.vtf = vtf.VTF(width, height, (7, 5), fmt=format, flags=flags)
			self.vtf.get().copy_from(im.tobytes('C'), format)
			self.vtf.save(self.file)


implugins.formats.add_format(VtfFormat("VTF", "Implements the Valve Texture Format", ["vtf", "vtfd"], "i"))