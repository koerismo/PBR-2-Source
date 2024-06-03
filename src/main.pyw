from PIL.ImageOps import flip
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QErrorMessage, QFileDialog, QPushButton
from gui import mainWin
from pathlib import Path
from math import log2
import logging
logging.getLogger().setLevel( 20 )

from os.path import join as joinPath
from tempfile import gettempdir

from PIL import Image, ImageChops
from srctools import VTF
from srctools.vtf import ImageFormats as VTFFormats

class frontend( mainWin ):
	def __init__( self ):
		super().__init__()

		self.data = {
			'OutputShader': ('LightmappedGeneric',False),
			'OutputEnvmap': None,
			'OutputReflectIntensity': 30,
			'ImageDiffuse': None,
			'ImageRoughness': None,
			'ImageMetallic': None,
			'ImageNormal': None,
			'SizeOverride': False,
			'VTFVersion': (7, 5),
			'OutputDiffuseTransparency': False
		}

		self.exportBtn.setDisabled( True )

	def setProperty( self, property, value ):
		self.data[property] = value

		self.exportBtn.setEnabled( all([
			self.data['ImageDiffuse'],
			self.data['ImageRoughness'],
			self.data['ImageMetallic'],
			self.data['ImageNormal']
		]) )

	def getPathRelative( self, origpath:Path ):
		newpath = origpath
		while newpath.name != 'materials' and newpath != newpath.parent:
			newpath = newpath.parent
		
		if newpath == newpath.parent: return None
		return origpath.relative_to( newpath )
	
	def removeSuffix( self, path:Path ):
		if path is None: return None
		return Path( str(path)[:-len(path.suffix)] )

	def doExport( self ):

		''' ---------- CHECK IMAGES ---------- '''

		def checkImageSize( img ):
			def isPowerOfTwo( v ): return log2(v)%1 == 0
			return isPowerOfTwo(img.width) and isPowerOfTwo(img.height)

		if not checkImageSize( self.data['ImageDiffuse'] ) and not self.data['SizeOverride']:
			msg = QErrorMessage( self )
			msg.showMessage( 'Basetexture has a non-power of two size!' )
			msg.activateWindow()
			return


		''' ---------- DO PATH MAGIC ---------- '''

		rawpath = QFileDialog.getSaveFileName( caption='Create material', filter='Valve Material Type (*.vmt)' )
		if not len(rawpath[0]): return
		path = rawpath[0]

		vmtPathRelative = self.removeSuffix(self.getPathRelative( Path(path) ))

		if vmtPathRelative is None:
			msg = QErrorMessage( self )
			msg.setWindowTitle( 'Error' )
			msg.showMessage( 'Failed to find materials directory! Be sure that you are exporting into a content folder.' )
			msg.activateWindow()
			return

		vmtPathStr = str( vmtPathRelative ).replace( '\\', '/' )
		vmtDirRelative = vmtPathRelative.parent


		''' ---------- WRITE VMT ---------- '''
		logging.info(' Creating VMT... ')

		self.exportBtn.setDisabled( True )
		#for child in self.findChildren( QPushButton, 'disableWhenExporting', Qt.FindChildrenRecursively ): child.setDisabled( True )

		self.progressBar.setValue( 1 )

		with open( path, 'w' ) as vmt:

			# BASETEXTURE & BUMP

			vmt.writelines([
				'"'+self.data['OutputShader'][0]+'"\n',
				'{\n',
				'	$basetexture               "'+vmtPathStr+'_basecolor"\n',
				'	$bumpmap                   "'+vmtPathStr+'_bump"\n'
			])

			# TRANSPARENCY

			if self.data['OutputDiffuseTransparency']:
				vmt.writelines([
					'	$translucent               1\n'
				])

			# MRAO

			if self.data['OutputShader'][0] == 'PBR':
				vmt.writelines([
					'	$mraotexture               "'+vmtPathStr+'_mrao"\n',
				])

			# ENVMAP

			if self.data['OutputEnvmap'] != None:
				vmt.writelines([
					'\n',
					'	$envmap                    "'+self.data['OutputEnvmap']+'"\n',
					'	$normalmapalphaenvmapmask  1\n'
				])
				if self.data['OutputShader'][0] != 'PBR':
					vmt.writelines([
						'\n',
						'	$envmaptint                '+str(round(self.data['OutputReflectIntensity']/100,2))+'\n',
						'	$envmaplightscale          0.98\n'
					])

			# $MODEL

			if self.data['OutputShader'][1]:
				vmt.writelines([
					'\n',
					'    $model 1\n'
				])
			
			vmt.write('}')

		''' ---------- BEGIN IMAGE PROCESSING ---------- '''
		logging.info(' Processing images... ')

		self.progressBar.setValue( 2 )

		def crossChannels( tex1:Image, chan1:int, tex2:Image, chan2:int ):
			'''Takes a channel from tex1 and replaces the contents of tex2's chan2'''
			r1, g1, b1, a1 = tex1.convert('RGBA').split()
			r2, g2, b2, a2 = tex2.convert('RGBA').split()
			match chan1:
				case 0: src = r1
				case 1: src = g1
				case 2: src = b1
				case 3: src = a1
			match chan2:
				case 0: r2 = src
				case 1: g2 = src
				case 2: b2 = src
				case 3: a2 = src
			return Image.merge( 'RGBA', (r2, g2, b2, a2) )

		# Register basetexture

		BaseTexture = self.data['ImageDiffuse'].convert('RGBA')
		if self.data['SizeOverride']: BaseTexture = BaseTexture.resize( (self.data['SizeOverride'], self.data['SizeOverride']) )

		# Register AO, Apply AO to basetexture

		AOTexture = Image.new( 'RGBA', BaseTexture.size, 255 )
		if self.data.get('ImageAo') != None:
			# Replace the placeholder with the actual texture, but erase the alpha channel.
			AOTexture = crossChannels(AOTexture, 3, self.data['ImageAo'].resize( BaseTexture.size ), 3)
			
			if self.data['OutputShader'][0] != 'PBR':
				BaseTexture = ImageChops.multiply( BaseTexture, AOTexture )

		# Register metallic
		MetallicTexture = self.data['ImageMetallic'].convert('RGB').resize( BaseTexture.size )

		# Register roughness
		RoughnessTexture = self.data['ImageRoughness'].convert('RGB').resize( BaseTexture.size )

		''' ---------- PROCESS MRAO (PBR) ---------- '''

		if self.data['OutputShader'][0] == 'PBR':
			MRAOTexture = Image.new( 'RGB', BaseTexture.size, 255 )
			MRAOTexture = crossChannels( MetallicTexture, 0, MRAOTexture, 0 )
			MRAOTexture = crossChannels( RoughnessTexture, 0, MRAOTexture, 1 )
			MRAOTexture = crossChannels( AOTexture, 0, MRAOTexture, 2 )



		''' ---------- PROCESS NORMAL MAP ---------- '''

		self.progressBar.setValue( 3 )

		NormalTexture = self.data['ImageNormal'].convert('RGB').resize( BaseTexture.size )

		if self.checkFlipY.isChecked():
			def flipG( tex ):
				r, g, b = tex.split()
				g = ImageChops.invert(g)
				return Image.merge( 'RGB', (r, g, b) )
			NormalTexture = flipG( NormalTexture )

		# Apply metallic to roughness, and add resulting specularity as a mask to normal map. (ONLY IF REFLECTIONS ARE ENABLED AND NOT IN PBR MODE)
		if self.data['OutputEnvmap'] != None and self.data['OutputShader'][0] != 'PBR':
			RoughnessTexture = ImageChops.multiply( ImageChops.invert(RoughnessTexture), MetallicTexture )
			NormalTexture = crossChannels( RoughnessTexture, 0, NormalTexture, 3 )

		''' ---------- CONVERT IMAGES ---------- '''
		logging.info(' Converting images... ')
		
		self.progressBar.setValue( 4 )

		def PILToVTF( img:Image, fmt ) -> VTF:
			v = VTF( img.width, img.height, frames=1, fmt=fmt, version=self.data['VTFVersion'] )
			v.get( frame=0 ).copy_from( img.convert('RGBA').tobytes() )
			return v

		if self.data['OutputShader'][0] == 'PBR':
			NormalTextureVTF = PILToVTF( NormalTexture, VTFFormats.DXT1 )
			MRAOTextureVTF = PILToVTF( MRAOTexture, VTFFormats.DXT1 )
		else:
			if self.data['OutputEnvmap'] == None:
				NormalTextureVTF = PILToVTF( NormalTexture, VTFFormats.RGB888 )
			else:
				NormalTextureVTF = PILToVTF( NormalTexture, VTFFormats.RGBA8888 )
		
		if self.data['OutputDiffuseTransparency']:
			BaseTextureVTF = PILToVTF( BaseTexture, VTFFormats.DXT5 )
		else:
			BaseTextureVTF = PILToVTF( BaseTexture, VTFFormats.DXT1 )

		targetDir = str( self.removeSuffix(Path(path)) )


		''' ---------- SAVE IMAGES ---------- '''
		logging.info(' All processing complete! Saving images... ')

		with open( targetDir+'_basecolor.vtf', 'wb' ) as targetfile:
			BaseTextureVTF.save( targetfile )
		with open( targetDir+'_bump.vtf', 'wb' ) as targetfile:
			NormalTextureVTF.save( targetfile )
		if self.data['OutputShader'][0] == 'PBR':
			with open( targetDir+'_mrao.vtf', 'wb' ) as targetfile:
				MRAOTextureVTF.save( targetfile )

		self.progressBar.setValue( 5 )
		logging.info(' All files saved successfully! ')

		msgBox = QMessageBox()
		msgBox.setWindowTitle( self.windowTitle() )
		msgBox.setText( 'Export successful!' )
		msgBox.exec()

		self.exportBtn.setDisabled( False )
		#for child in self.findChildren( QPushButton, 'disableWhenExporting', Qt.FindChildrenRecursively ): child.setDisabled( False )
		self.progressBar.reset()

		
		


app = QApplication()
win = frontend()
win.show()
app.exec()