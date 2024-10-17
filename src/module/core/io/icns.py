from struct import Struct

s_file_header = Struct(">4sI")
s_icon_data_header = Struct(">4sI")
# s_toc_entry = Struct(">4s")

class ICNS:
	def __init__(self) -> None:
		pass

	# @classmethod
	# def write_chunks(cls, chunks: list[tuple[bytes, bytes]]) -> bytes:
	# 	file_length = 8
	# 	for chunk_id, chunk in chunks: file_length += 8 + len(chunk)
	
	# 	buffer = bytearray()
	# 	buffer.extend(s_file_header.pack(b'icns', file_length))

	# 	i = 0
	# 	for chunk_id, chunk in chunks:
	# 		buffer.extend(s_icon_data_header.pack(chunk_id, len(chunk) + 8))
	# 		buffer.extend(chunk)
	# 		i += len(chunk) + 8

	# 	return buffer

	@classmethod
	def get_chunk(cls, data: bytes, ident: bytes) -> bytes|None:
		magic, file_length = s_file_header.unpack_from(data)
		assert magic == b'icns'
		i = 8

		while i < len(data):
			chunk_type, chunk_length = s_icon_data_header.unpack_from(data, i)
			if chunk_type == ident: return data[i+8 : i+chunk_length]
			i += chunk_length

		return None

	@classmethod
	def get_icon(cls, data: bytes, size: int=256, variant: bytes|None=None) -> bytes|None:
		ident = b'icp4'
		if   size == 128: ident = b'ic07'
		elif size == 256: ident = b'ic08'
		elif size == 512: ident = b'ic09'
		elif size == 1024: ident = b'ic10'
		elif size == 32: ident = b'ic11'
		elif size == 64: ident = b'ic12'


		if variant == None:
			subicon = cls.get_chunk(data, ident)
			assert subicon, 'Failed to read icon chunk!'
			return subicon

		subfile = cls.get_chunk(data, variant)
		assert subfile, 'Failed to read icon chunk!'
		return cls.get_chunk(subfile, ident)


# if __name__ == '__main__':
# 	def open_png(p: str) -> bytes:
# 		with open(p, 'rb') as f:
# 			return f.read()
	
# 	with open('./res/icon.icns', 'wb') as f:
# 		f.write(ICNS.write_chunks([
# 			(b'ic08', open_png('./res/icon1.png')),
# 			(b'stpr', ICNS.write_chunks([
# 				(b'ic08', open_png('./res/icon2.png'))
# 			]))
# 		]))
