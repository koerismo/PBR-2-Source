from PIL.Image import Image
import PIL.Image
from .material import Material, MaterialMode
from . import texops

def from_images(src: dict[str, Image], name: str, mode: MaterialMode) -> "Material":
	albedo = src.get('albedo')
	normal = src.get('normal')

	assert albedo is not None
	assert normal is not None

	specular = src.get('specular')
	if specular is None:
		metallic = src.get('metallic')
		if metallic is None:
			specular = PIL.Image.new('L', normal.size, 255)
		else:
			(albedo, specular) = texops.convert_albedo_specular(albedo, metallic)

	glossy = src.get('glossy')
	if glossy is None:
		rough = src.get('rough')
		assert rough is not None
		glossy = texops.convert_glossy(rough)

	emit = src.get('emit')
	ao = src.get('ao')
	height = src.get('height')

	return Material(
		mode,
		normal.size,
		name,
		texops.normalize(albedo),
		texops.normalize(specular, normal.size),
		texops.normalize(glossy, normal.size),
		texops.normalize(emit, albedo.size) if emit else None,
		texops.normalize(ao, albedo.size) if ao else None,
		texops.normalize(normal),
		texops.normalize(height, normal.size) if height else None
	)
