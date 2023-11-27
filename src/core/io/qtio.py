from pathlib import Path
from .image import Image, IOBackend

from PySide6.QtGui import QImage, QColorSpace, QColor
from PySide6.QtCore import Qt

import numpy as np
from srctools.vtf import VTF, VTFFlags, ImageFormats

class QtIOBackend(IOBackend):
	@staticmethod
	def load(path: str|Path) -> Image:
		im = QImage()
		im.load(str(path))
		im = im.convertedTo(QImage.Format.Format_RGBA8888, Qt.ImageConversionFlag.NoOpaqueDetection)
		ptr = im.constBits()
		src = np.array(ptr).reshape(im.width(), im.height(), 4)
		return Image(src)

	@staticmethod
	def save(image: Image, path: str | Path, version: int=5) -> None:
		height, width, bands = image.data.shape

		path = Path(path)
		if path.suffix !='.vtf':
			raise NotImplementedError(f'Failed to save {path.name} . Use imageio backend for non-vtf output!')

		format = None
		flags = VTFFlags.EMPTY
		match (bands, image.data.dtype):
			case (1, 'uint8'): format = ImageFormats.I8
			case (3, 'uint8'): format = ImageFormats.RGB888
			case (4, 'uint8'):
				format = ImageFormats.RGBA8888
				flags |= VTFFlags.EIGHTBITALPHA
			case (4, 'uint16'):
				format = ImageFormats.RGBA16161616
				flags |= VTFFlags.EIGHTBITALPHA
			case (4, 'float16'):
				format = ImageFormats.RGBA16161616F
				flags |= VTFFlags.EIGHTBITALPHA

		if format is None:
			raise TypeError(f"Could not match format {image.data.dtype}x{bands}!")

		vtf = VTF(width, height, (7, version), fmt=format, flags=flags)
		vtf.get().copy_from(image.data.tobytes('C'), format)

		with open(path, 'wb') as file:
			vtf.save(file)

# def apply_gamma(image: QImage, gamma: float) -> None:
# 	for y in range(0, image.height()):
# 		for x in range(0, image.width()):
# 			col = image.pixelColor(x, y)
# 			col.setRedF(col.redF() ** gamma)
# 			col.setGreenF(col.greenF() ** gamma)
# 			col.setBlueF(col.blueF() ** gamma)
# 			col.setAlphaF(col.alphaF() ** gamma)
# 			image.setPixelColor(x, y, col)

def load(path: str) -> Image:
	image = QImage()
	image.load(path)

	# color_space = image.colorSpace()
	# gamma = color_space.gamma()
	# description = color_space.description()
	# print(path.split('\\')[-1], color_space.gamma(), color_space.primaries(), color_space.description())

	# if description == "sRGB IEC61966-2.1":
	# 	print('Attempting to adjust gamma of image', path.split('\\')[-1], 'from', color_space.description())
	# 	apply_gamma(image, 1.3)
	#	image.setColorSpace(QColorSpace.NamedColorSpace.sRgbLinear)

	image = image.convertedTo(QImage.Format.Format_RGBA8888, Qt.ImageConversionFlag.NoOpaqueDetection)
	ptr = image.constBits()
	arr = np.array(ptr).reshape(image.width(), image.height(), 4)
	return Image(arr)


def export(image: Image, path: str, version: int):
	data = image.data
	if not isinstance(data, np.ndarray):
		raise TypeError(f"Vtf writer expected nparray, but got {type(data)} instead!")

	height, width, bands = data.shape

	format = None
	flags = VTFFlags.EMPTY
	match (bands, data.dtype):
		case (1, 'uint8'): format = ImageFormats.I8
		case (3, 'uint8'): format = ImageFormats.RGB888
		case (4, 'uint8'):
			format = ImageFormats.RGBA8888
			flags |= VTFFlags.EIGHTBITALPHA
		case (4, 'uint16'):
			format = ImageFormats.RGBA16161616
			flags |= VTFFlags.EIGHTBITALPHA
		case (4, 'float16'):
			format = ImageFormats.RGBA16161616F
			flags |= VTFFlags.EIGHTBITALPHA

	if format is None:
		raise TypeError(f"Could not match format {data.dtype}x{bands}!")

	vtf = VTF(width, height, (7, version), fmt=format, flags=flags)
	vtf.get().copy_from(data.tobytes('C'), format)

	with open(path, 'wb') as file:
		vtf.save(file)

# def resize(image: Image, size: tuple[int, int]):
# 	b = image.data.tobytes()
# 	width, height = image.size
# 	bpl = image.data.itemsize * width
# 	q = QImage(
# 		b, width, height
#     bpl,
#     QImage.Format.Format_RGBA32FPx4
# 	)