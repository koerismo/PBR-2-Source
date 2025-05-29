from pathlib import Path
from .image import Image, IOBackend

from PySide6.QtGui import QImage
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
	width, height = image.size
	bpp = image.channels
	data = image.convert(np.uint8).tobytes(np.uint8)

	format: QImage.Format
	match image.channels:
		case 1: format = QImage.Format.Format_Grayscale8
		case 3: format = QImage.Format.Format_RGB888
		case 4: format = QImage.Format.Format_RGBA8888
		case count:
			raise Exception(f'Cannot convert Image to QImage with {count} channels!')

	qimage = QImage(data, width, height, bpp*width, format)
	if qimage.isNull():
		raise Exception(f'QImage is null: Failed to convert the data to an acceptable format? Report this issue!')

	return qimage

def qimage_to_image(qimage: QImage) -> Image:
	''' Converts a Qt QImage to an Image. (U8/F16x4) '''
	channels: int
	dtype = np.uint8
	match qimage.format():
		case QImage.Format.Format_Grayscale8: channels = 1
		case QImage.Format.Format_RGB888: channels = 3
		case QImage.Format.Format_RGBA8888: channels = 4
		case _:
			channels = 4
			dtype = np.float16
			qimage = qimage.convertToFormat(QImage.Format.Format_RGBA16FPx4)

	ptr = qimage.constBits()
	data = np.frombuffer(ptr, dtype=dtype).copy().reshape(qimage.height(), qimage.width(), channels)
	return Image(data)

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
			case (4, 'float16'):
				format = ImageFormats.RGBA16161616F
				flags |= VTFFlags.EIGHTBITALPHA
				max_value = 1.0

		if format == None:
			raise TypeError(f"Could not match format {image.data.dtype}x{bands}!")

		if target_format == None:
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
		# TODO: Verify fixes. AGAIN.
		qimage = image_to_qimage(image)
		scaled = qimage.scaled(dims[0], dims[1], Qt.AspectRatioMode.IgnoreAspectRatio)
		return qimage_to_image(scaled)
