from pathlib import PurePath
from io import StringIO

def generate_vmt(
		path: PurePath,
		model=True,
		pbr=False,
		alpha=0,
		emit=False,
		envmap='env_cubemap',
		phong=False,
		parallax=False ) -> tuple[str, dict]:
	mat_path = path.parent
	mat_name = path.name[:-len(path.suffix)]
	info = {
		'emit_embedded_albedo': emit and not ( pbr or alpha ),				# Whether emission is stored in the albedo
		'phong_embedded_albedo': phong and not ( pbr or alpha or emit ),	# Whether phong intensity is stored in the albedo
		'phong_embedded_normal': phong and not pbr and ( alpha or emit ),	# Whether phong intensity is stored in the normal
		'height_embedded_normal': pbr and parallax,							# Whether height is being stored in the normal
	}

	buffer = StringIO()

	# Shader Name
	if pbr:		buffer.write('PBR')
	else:		buffer.write( 'VertexLitGeneric' if model else 'LightmappedGeneric' )
	buffer.write('\n{\n')

	# Shader Basics
	buffer.write(					f'	$basetexture		"{mat_path}/{mat_name}_albedo"\n'	)
	buffer.write(					f'	$bumpmap			"{mat_path}/{mat_name}_bump"\n'		)
	if envmap:		buffer.write(	f'	$envmap				"{envmap}"\n'						)

	# Alpha
	if alpha == 1:	buffer.write(f'\n	$alphatest			1\n'	)
	if alpha == 2:	buffer.write(f'\n	$translucent		1\n'	)

	# PBR-specific
	if pbr:
		buffer.write(			f'\n	$mraotexture		"{mat_path}/{mat_name}_mrao"\n'		)
		if emit:		buffer.write(f'	$emissiontexture	"{mat_path}/{mat_name}_emit"\n'		)
		if parallax:	buffer.write(f'	$parallax			1\n'								)
		buffer.write(				f'	$model				{int(model)}\n'						)

	# Standard-specific
	else:
		if phong:
			buffer.write(	f'\n	$phong					1\n'							)
			buffer.write(		f'	$phongboost				1.0\n'							)
			buffer.write(		f'	$phongfresnelranges		"[0 0.5 1]"\n'					)

			if info['phong_embedded_albedo']:
				buffer.write(	f'	$basemapalphaphongmask	1\n'							)
			else:
				buffer.write(	f'	$phongexponenttexture	"{mat_path}/{mat_name}_exp"\n'	)

		if emit:
			buffer.write(	f'\n	$selfillum				1\n'							)
			if not info['emit_embedded_albedo']:
				buffer.write(	f'	$selfillummask			"{mat_path}/{mat_name}_emit"\n'	)


	buffer.write('}')
	
	return buffer.getvalue(), info
