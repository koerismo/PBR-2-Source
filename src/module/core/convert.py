from .material import Material, MaterialMode, Texture
from . import texops

def export(src: Material) -> list[Texture]:
	textures = []
	basecolor = texops.make_basecolor(src)
	basecolor = basecolor.resize(src.size)
	basecolor = basecolor.convert('uint8', clip=True)
	textures.append(Texture(basecolor, '_albedo'))

	bumpmap = texops.make_bumpmap(src)
	bumpmap = bumpmap.convert('uint8', clip=True)
	textures.append(Texture(bumpmap, '_bump', compressed=False))

	if (MaterialMode.has_selfillum(src.mode) or MaterialMode.is_pbr(src.mode)) and src.emit:
			emit = texops.make_emit(src)
			illum_mask = emit.convert('uint8')
			textures.append(Texture(illum_mask, '_emit'))

	if MaterialMode.is_pbr(src.mode):
		mrao = texops.make_mrao(src)
		mrao = mrao.convert('uint8')
		textures.append(Texture(mrao, '_mrao'))
		
	else:
		if MaterialMode.has_phong(src.mode):
			phong_exp = texops.make_phong_exponent(src)
			phong_exp = phong_exp.convert('uint8', clip=True)
			textures.append(Texture(phong_exp, '_phongexp'))

		if MaterialMode.has_envmap(src.mode) and not MaterialMode.embed_envmap(src.mode):
			envmap_mask = texops.make_envmask(src)
			envmap_mask = envmap_mask.convert('uint8', clip=True)
			textures.append(Texture(envmap_mask, '_envmap'))

	return textures
