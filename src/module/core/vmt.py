from .material import Material, MaterialMode, GameTarget
from .config import get_config, TargetRole


'''
"VertexLitGeneric"
{
	$basetexture "pbr2source_test0_albedo"
	$bumpmap "pbr2source_test0_bump"

	$envmap "env_cubemap"
	$envmaptint "[.05 .05 .05]"
	$envmapcontrast 1.0

	$phong 1
	$phongfresnelranges "[0.2 0.8 1.0]"
	$phongexponenttexture "pbr2source_test0_phongexp"
	$phongboost 1.0
}
'''

def game_envmaptint(game: GameTarget, vlg: bool) -> float:
	if game > GameTarget.V2011: return 1.0
	return .1 if vlg else round(.1**2.2, ndigits=4)

def game_lightscale(game: GameTarget) -> float|None:
	if game > GameTarget.V2011: return 1.0
	if game == GameTarget.VGMOD: return 1.0
	return None


def make_vmt(mat: Material) -> str:
	pbr    = MaterialMode.is_pbr(mat.mode)
	shader = MaterialMode.get_shader(mat.mode)
	vmt    = []

	texRoles = get_config().targets
	T = TargetRole

	def post(role: TargetRole):
		return texRoles[role].postfix.rsplit('.', 2)[0]

	def write(*args: str):
		l = len(vmt)
		vmt[l:l+len(args)] = args

	write(			f'{shader}\n{{',
					f'	$basetexture		"{mat.name}{post(T.Basecolor)}"',
					f'	$bumpmap			"{mat.name}{post(T.Bumpmap)}"' )

	if MaterialMode.has_alpha(mat.mode):
		write(		'	$translucent	1')

	if pbr:
		write(
					'',
					f'	$mraotexture		"{mat.name}{post(T.Mrao)}"',
					f'	$model				{int(MaterialMode.is_model(mat.mode))}' )

		if mat.emit:
			write(
					f'	$emissiontexture	"{mat.name}{post(T.Emit)}"')
		if mat.height:
			write(
					'',
					'	$parallax			1',
					'	$parallaxdepth		0.04',
					'	$parallaxcenter		0.5')

	else:
		envmaptint = game_envmaptint(mat.target, MaterialMode.is_vlg(mat.mode))
		lightscale = game_lightscale(mat.target)

		# Do we use envmaps?
		if MaterialMode.has_envmap(mat.mode):
			write(
					'',
					f'	$envmap						"env_cubemap"',
					f'	$envmaptint					"[{envmaptint} {envmaptint} {envmaptint}]"',
					'	$envmapcontrast				1.0' )


			# Packed envmap
			if MaterialMode.embed_envmap(mat.mode):
				if Material.swap_phong_envmap(mat):
					write(
					'	$normalmapalphaenvmapmask	1',
					'	$basemapalphaphongmask		1')
				else:
					write(
					'	$basetextureenvmapmask		1')
			# Unpacked envmap
			else:
				write(
					f'	$envmapmask					"{mat.name}{post(T.EnvmapMask)}"')
				
				# Enable fresnel for envmap always
				if MaterialMode.is_vlg(mat.mode): write(
					f'	$envmapfresnel				1')
				else: write(
					f'	$fresnelreflection			0')


		# Does the game support lightscale?
		if lightscale:
			write(
					f'	$envmaplightscale			{lightscale}' )


		# Phong base
		if MaterialMode.has_phong(mat.mode):
			write(
					'',
					'	$phong 1',
					f'	$phongexponenttexture		"{mat.name}{post(T.PhongExp)}"',
					'	$phongexponentfactor		32.0',
					'	$phongboost					5.0')

		# Are envmap or phong using the fresnel ranges?
		if MaterialMode.has_phong(mat.mode) or MaterialMode.has_envmap(mat.mode):
			write(	'	$phongfresnelranges			"[0.1 0.8 1.0]"')


		# Do we need to handle self-illumination?
		if MaterialMode.has_selfillum(mat.mode):
			write(	'',
					f'	$detail				"{mat.name}{post(T.Emit)}"'
					'	$detailscale		1',
					'	$detailblendmode	5')
	write('}')
	return '\n'.join(vmt)
