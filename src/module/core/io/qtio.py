from pathlib import Path
from .image import Image, IOBackend

from PySide6.QtGui import QImage
from PySide6.QtCore import Qt

import numpy as np
from typing import IO
from sourcepp import vtfpp
ImageFormats = vtfpp.ImageFormat

qimage_test: QImage|None = None

def load_vtf(file: IO[bytes]):
	vtf = vtfpp.VTF(file.read())
	frame: bytes = vtf.get_image_data_as_rgba8888()
	data = (np.frombuffer(frame, dtype=np.uint8).astype(np.float32) / 255.0).reshape((vtf.width_for_mip(0), vtf.height_for_mip(0), 4))
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
	assert ptr != None, 'Failed to get QImage data handle. This might mean that the file could not be accessed!'

	data = np.frombuffer(ptr, dtype=dtype).copy().reshape(qimage.height(), qimage.width(), channels)
	return Image(data)

class QtIOBackend(IOBackend):
	@staticmethod
	def load_qimage(path: str|Path) -> QImage:
		if (str(path).endswith('.vtf')):
			with open(path, 'rb') as file:
				return image_to_qimage(load_vtf(file))
			
		im = QImage()
		assert im.load(str(path)), 'Failed to load image!'
		return im

	@staticmethod
	def load(path: str|Path) -> Image:
		if (str(path).endswith('.vtf')):
			with open(path, 'rb') as file:
				return load_vtf(file)

		return qimage_to_image(QtIOBackend.load_qimage(path))

	@staticmethod
	def save(image: Image, path: str | Path, version=4, lossy=True, zip=False, flags=0, mipmaps=-1, mipmapFilter=vtfpp.ImageConversion.ResizeFilter.DEFAULT, **kwargs) -> bool:
		height, width, bands = image.data.shape

		path = Path(path)
		if path.suffix !='.vtf':
			return image_to_qimage(image).save(str(path))

		format = None
		target_format = None
		is_strata = version == 6

		match (bands, image.data.dtype):
			case (1, 'uint8'):
				format = ImageFormats.I8
			case (3, 'uint8'):
				format = ImageFormats.RGB888
				if lossy: target_format = ImageFormats.DXT1
				elif is_strata: target_format = ImageFormats.RGBA8888 # TODO: Expand this to any DX11 game
			case (4, 'uint8'):
				format = ImageFormats.RGBA8888
				if lossy: target_format = ImageFormats.BC7 if is_strata else ImageFormats.DXT5
				flags |= vtfpp.VTF.Flags.V0_MULTI_BIT_ALPHA.value
			case (4, 'float16'):
				format = ImageFormats.RGBA16161616F
				if lossy and is_strata: target_format = ImageFormats.BC6H
				flags |= vtfpp.VTF.Flags.V0_MULTI_BIT_ALPHA.value

		if format == None:
			raise TypeError(f"Could not match format {image.data.dtype}x{bands}!")

		if target_format == None:
			target_format = format

		vtf = vtfpp.VTF()
		vtf.set_image(image.data.tobytes('C'), format, width, height, mipmapFilter)
		vtf.version = version
		vtf.flags = flags

		if mipmaps != -1:	vtf.mip_count = mipmaps
		else:				vtf.set_recommended_mip_count()

		vtf.compute_mips(mipmapFilter)
		vtf.set_format(target_format, quality=1)

		if is_strata and zip:
			vtf.compression_level = -1

		with open(path, 'wb') as file:
			data = vtf.bake()
			file.write(data)

		return True
	
	@staticmethod
	def resize(image: Image, dims: tuple[int, int]) -> Image:
		# TODO: This causes segfaults sometimes. WTF?
		# TODO: Verify fixes. AGAIN.
		qimage = image_to_qimage(image)
		scaled = qimage.scaled(dims[0], dims[1], Qt.AspectRatioMode.IgnoreAspectRatio)
		return qimage_to_image(scaled)
