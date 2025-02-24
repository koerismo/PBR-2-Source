from pathlib import Path
from .image import Image, IOBackend

from PySide6.QtGui import QImage, QColorSpace, QColor
from PySide6.QtCore import Qt

import numpy as np
from srctools.vtf import VTF, VTFFlags, ImageFormats
from typing import IO

qimage_test: QImage|None = None

def load_vtf(file: IO[bytes]):
	vtf = VTF.read(file)
	frame = vtf.get()
	frame.load()
	data = (np.array(frame._data) / 255.0).reshape((frame.width, frame.height, 4))
	return Image(data)

def image_to_qimage(image: Image) -> QImage:
	''' Converts an Image to a Qt QImage. (U8) '''
	size = image.size
	return QImage(image.tobytes(np.float16), size[0], size[1], QImage.Format.Format_RGBA16FPx4)

def qimage_to_image(im: QImage) -> Image:
	''' Converts a Qt QImage to an Image. (U8) '''
	im = im.convertToFormat(QImage.Format.Format_RGBA16FPx4)
	ptr = im.constBits()
	# TODO: Yes, width/height are swapped intentionally. No, I don't completely understand it either.
	src = np.frombuffer(ptr, dtype=np.float16).copy().reshape(im.height(), im.width(), 4)
	return Image(src)

class QtIOBackend(IOBackend):
	@staticmethod
	def load_qimage(path: str|Path) -> QImage:
		if (str(path).endswith('.vtf')):
			with open(path, 'rb') as file:
				return image_to_qimage(load_vtf(file))
			
		im = QImage()
		im.load(str(path))
		return im

	@staticmethod
	def load(path: str|Path) -> Image:
		if (str(path).endswith('.vtf')):
			with open(path, 'rb') as file:
				return load_vtf(file)

		return qimage_to_image(QtIOBackend.load_qimage(path))

	@staticmethod
	def save(image: Image, path: str | Path, version: int=4, compressed: bool=True) -> None:
		height, width, bands = image.data.shape

		path = Path(path)
		if path.suffix !='.vtf':
			raise NotImplementedError(f'Failed to save {path.name} . Use imageio backend for non-vtf output!')

		format = None
		target_format = None

		max_value = 255
		flags = VTFFlags.EMPTY
		match (bands, image.data.dtype):
			case (1, 'uint8'):
				format = ImageFormats.I8
			case (3, 'uint8'):
				if compressed:	target_format = ImageFormats.DXT1
				format = ImageFormats.RGB888
			case (4, 'uint8'):
				if compressed:	target_format = ImageFormats.DXT5
				format = ImageFormats.RGBA8888
				flags |= VTFFlags.EIGHTBITALPHA
			case (4, 'uint16'):
				format = ImageFormats.RGBA16161616
				flags |= VTFFlags.EIGHTBITALPHA
				max_value = 0xffff
			case (4, 'float16'):
				format = ImageFormats.RGBA16161616F
				flags |= VTFFlags.EIGHTBITALPHA
				max_value = 1.0

		if format is None:
			raise TypeError(f"Could not match format {image.data.dtype}x{bands}!")

		if target_format is None:
			target_format = format

		vtf = VTF(width, height, (7, version), fmt=target_format, flags=flags)
		vtf.get().copy_from(image.data.tobytes('C'), format)
		
		# Use color for reflectivity
		average = image.average()
		if bands >= 3:
			vtf.reflectivity.x = average[0] / max_value
			vtf.reflectivity.y = average[1] / max_value
			vtf.reflectivity.z = average[2] / max_value
		else:
			amount = average[0] / max_value
			vtf.reflectivity.x = amount
			vtf.reflectivity.y = amount
			vtf.reflectivity.z = amount


		with open(path, 'wb') as file:
			vtf.save(file)
	
	@staticmethod
	def resize(image: Image, dims: tuple[int, int]) -> Image:
		# TODO: This causes segfaults sometimes. WTF?
		qimage = image_to_qimage(image)
		qimage = qimage.scaled(dims[0], dims[1], Qt.AspectRatioMode.IgnoreAspectRatio)
		return qimage_to_image(qimage)

# def apply_gamma(image: QImage, gamma: float) -> None:
# 	for y in range(0, image.height()):
# 		for x in range(0, image.width()):
# 			col = image.pixelColor(x, y)
# 			col.setRedF(col.redF() ** gamma)
# 			col.setGreenF(col.greenF() ** gamma)
# 			col.setBlueF(col.blueF() ** gamma)
# 			col.setAlphaF(col.alphaF() ** gamma)
# 			image.setPixelColor(x, y, col)

def DEPRECATED_load(path: str) -> Image:
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