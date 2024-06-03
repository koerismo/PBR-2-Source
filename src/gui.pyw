from PySide6 import QtCore, QtGui, QtWidgets as q
from PIL.ImageQt import ImageQt
from PIL import Image
from PIL.ImageOps import grayscale

class mainWin( q.QWidget ):
	def __init__( self ):
		super().__init__()

		self.setWindowTitle( 'PBR-2-Source' )
		self.resize( 600, 350 )

		''' --------------- LAYOUT --------------- '''

		self.layout = q.QVBoxLayout( self )

		self.innerLayout = q.QHBoxLayout()
		self.layout.addLayout( self.innerLayout )

		self.footer = q.QHBoxLayout()
		self.layout.addLayout( self.footer )

		''' --------------- INPUT  --------------- '''

		self.boxIn = q.QGroupBox( 'PBR Input' )
		self.innerLayout.addWidget( self.boxIn )

		self.inputLayout = q.QGridLayout( self.boxIn )
		self.inputLayout.setHorizontalSpacing( 1 )
		self.inputLayout.setAlignment( QtCore.Qt.AlignTop )

		def addInputForm( name, row, caption, BW ):
			label = q.QLabel()
			label.setFixedSize( 48, 48 )
			label.setBackgroundRole( QtGui.QPalette.ColorRole.Mid )
			label.setAutoFillBackground( True )
			label.setObjectName('previewImage')

			self.inputLayout.addWidget( label, row, 0, 2, 1 )
			self.inputLayout.addWidget( q.QLabel(name), row, 1, 1, 2, alignment=QtCore.Qt.AlignRight )
			btn = q.QPushButton( 'Browse' )
			btn.setFixedWidth( 50 )
			self.inputLayout.addWidget( btn, row+1, 1, alignment=QtCore.Qt.AlignRight )
			lineedit = q.QLineEdit()
			lineedit.setDisabled( True )
			lineedit.setAlignment( QtCore.Qt.AlignRight )
			self.inputLayout.addWidget( lineedit, row+1, 2 )

			def handleBrowse():
				filepath = q.QFileDialog.getOpenFileName( caption=f'Select {caption} image', filter='Images (*.png *.jpg *.jpeg *.bmp *.tga)' )

				if filepath[0] != '':
					# Load image with PIL, then convert it to something QT can use.
					with Image.open( filepath[0] ) as img:
						if BW: img = grayscale(img)
						self.onImageLoaded( caption.capitalize(), img )
						qimg = ImageQt( img )

					pixmap = QtGui.QPixmap.fromImage( qimg )
					scaled = pixmap.scaled( QtCore.QSize(48, 48) )
					label.setPixmap( scaled )

					lineedit.setText( filepath[0] )

			btn.clicked.connect( handleBrowse )

		addInputForm( 'Diffuse', 0, 'diffuse', False )
		addInputForm( 'AO (Optional)', 2, 'ao', True )
		addInputForm( 'Roughness', 4, 'roughness', True )
		addInputForm( 'Metallic', 6, 'metallic', True )
		addInputForm( 'Normal Map', 8, 'normal', False )

		''' --------------- OUTPUT --------------- '''

		self.boxOut = q.QGroupBox( 'Source Output' )
		self.innerLayout.addWidget( self.boxOut )

		self.outputLayout = q.QVBoxLayout( self.boxOut )
		self.outputLayout.setAlignment( QtCore.Qt.AlignTop )
		self.outputLayout.setSpacing( 1 )

		# Export mode
		'''
		self.outputLayout.addWidget( q.QLabel('Export Mode') )

		exportModeLayout = q.QHBoxLayout()
		self.exportModeClassic = q.QPushButton( 'Classic' )
		self.exportModeClassic.setCheckable( True )
		self.exportModeClassic.setChecked( True )
		exportModeLayout.addWidget( self.exportModeClassic )
		self.exportModePBR = q.QPushButton( 'PBR' )
		self.exportModePBR.setCheckable( True )
		exportModeLayout.addWidget( self.exportModePBR )

		self.outputLayout.addLayout( exportModeLayout )
		'''



		self.outputLayout.addWidget( q.QLabel('Shader') )
		self.shaderInput = q.QComboBox()
		for a,b in [
			('Standard (Brush)', ('LightmappedGeneric', False)), # The second value in these tuples is whether they require `$model 1` to be inserted.
			('Standard (Model)', ('VertexLitGeneric', False)),
			('PBR (Brush)', ('PBR', False)),
			('PBR (Model)', ('PBR', True))
		]: self.shaderInput.addItem( a, b )

		def evalCustomShaderInput( x ):
			if (ind := self.shaderInput.findText( x )) != -1:
				dat = self.shaderInput.itemData(ind)
				
				# The PBR shader doesn't support this value, so just disable the slider and reset the value.
				self.reflectIntensityInput.setDisabled( dat[0] == 'PBR' )
				if dat[0] == 'PBR': self.reflectIntensityInput.setValue( 100 )
				
				self.setProperty( 'OutputShader', dat )

			else:
				self.setProperty( 'OutputShader', (x, False) )
		self.shaderInput.currentTextChanged.connect( evalCustomShaderInput )

		self.shaderInput.setEditable( True )
		self.shaderInput.setCurrentIndex(0)
		self.shaderInput.setInsertPolicy( q.QComboBox.NoInsert )
		self.outputLayout.addWidget( self.shaderInput )

		self.outputLayout.addSpacing( 10 )

		self.outputLayout.addWidget( q.QLabel('Reflections') )
		self.cubemapInput = q.QComboBox()
		for a,b in [
			('None', None),
			('Cubemap', 'env_cubemap'),
			('(P2) Black Wall 002a', 'metal/black_wall_envmap_002a'),
			('(CSGO) Generic Metal 01', 'environment maps/metal_generic_001'),
			('(CSGO) Generic Metal 02', 'environment maps/metal_generic_002'),
			('(CSGO) Generic Metal 03', 'environment maps/metal_generic_003'),
			('(CSGO) Generic Metal 04', 'environment maps/metal_generic_004'),
			('(CSGO) Generic Metal 05', 'environment maps/metal_generic_005'),
			('(CSGO) Generic Metal 06', 'environment maps/metal_generic_006')
		]: self.cubemapInput.addItem( a, b )

		self.cubemapInput.setEditable( True )
		self.cubemapInput.setInsertPolicy( q.QComboBox.NoInsert )
		self.cubemapInput.setCurrentIndex( 0 )
		self.outputLayout.addWidget( self.cubemapInput )

		# Handles when to take custom text and when to use the full path of the presets
		def evalCustomEnvmapInput( x ):
			if (ind := self.cubemapInput.findText( x )) != -1:
				self.setProperty( 'OutputEnvmap', self.cubemapInput.itemData(ind) )
			else:
				self.setProperty( 'OutputEnvmap', x )
		self.cubemapInput.currentTextChanged.connect( evalCustomEnvmapInput )

		self.outputLayout.addSpacing( 10 )
		
		reflectIntensityLabel = q.QLabel('Reflection Intensity (30%)')
		self.outputLayout.addWidget( reflectIntensityLabel )

		self.reflectIntensityInput = q.QSlider( QtCore.Qt.Horizontal )
		self.reflectIntensityInput.setRange( 0, 100 )
		self.reflectIntensityInput.setSingleStep( 5 )
		self.reflectIntensityInput.setValue( 30 )

		def onSliderUpdate(x):
			reflectIntensityLabel.setText(f'Reflection Intensity ({x}%)')
			self.setProperty( 'OutputReflectIntensity', x )

		self.reflectIntensityInput.valueChanged.connect( onSliderUpdate )
		self.outputLayout.addWidget( self.reflectIntensityInput )

		self.outputLayout.addStretch()

		self.imageOptionsGroup = q.QGroupBox( 'Image Options' )
		self.outputLayout.addWidget( self.imageOptionsGroup )
		self.imageOptionsGroup.layout = q.QVBoxLayout( self.imageOptionsGroup )

		self.checkFlipY = q.QCheckBox('Flip Normal Y')
		self.checkFlipY.setChecked( True )
		self.imageOptionsGroup.layout.addWidget( self.checkFlipY )


		self.transparencyInput = q.QCheckBox( 'Enable Transparency' )
		self.transparencyInput.stateChanged.connect( lambda x: self.setProperty('OutputDiffuseTransparency', bool(x)) )
		self.imageOptionsGroup.layout.addWidget( self.transparencyInput )


		self.resizeToInputLayout = q.QHBoxLayout()
		self.resizeToInputLayout.setAlignment( QtCore.Qt.AlignLeft )
		self.imageOptionsGroup.layout.addLayout( self.resizeToInputLayout )


		self.resizeToInputLayout.addWidget( q.QLabel('Resize:') )

		def handleResizeInputChange(x):
			if x == 0: self.setProperty( 'SizeOverride', False )
			else:      self.setProperty( 'SizeOverride', 32 * 2**x )

		self.resizeToInput = q.QComboBox()
		self.resizeToInput.addItems([ 'Don\'t Resize','64x','128x','256x','512x','1024x','2048x','4096x' ])
		self.resizeToInputLayout.addWidget( self.resizeToInput )
		self.resizeToInput.currentIndexChanged.connect( handleResizeInputChange )

		self.VTFVersionInputLayout = q.QHBoxLayout()
		self.VTFVersionInputLayout.setAlignment( QtCore.Qt.AlignLeft )
		self.imageOptionsGroup.layout.addLayout( self.VTFVersionInputLayout )

		self.VTFVersionInputLayout.addWidget( q.QLabel('VTF Version:') )

		def handleVTFVersionInputChange(x):
			self.setProperty( 'VTFVersion', (7, x+1) )

		self.vtfVersionInput = q.QComboBox()
		self.vtfVersionInput.addItems([ 'v7.1','v7.2','v7.3','v7.4','v7.5' ])
		self.vtfVersionInput.setCurrentIndex( 4 )
		self.vtfVersionInput.currentIndexChanged.connect( handleVTFVersionInputChange )
		self.VTFVersionInputLayout.addWidget( self.vtfVersionInput )

		''' --------------- FOOTER --------------- '''

		self.footer.setSpacing( 0 )

		self.progressBar = q.QProgressBar()
		self.progressBar.setRange( 0, 5 )
		self.progressBar.setFormat('%v/%m')
		self.footer.addWidget( self.progressBar )

		self.exportBtn = q.QPushButton( 'Export All' )
		self.footer.addWidget( self.exportBtn )
		self.exportBtn.clicked.connect( self.doExport )

	def setProperty( self, prop, val ):
		print(f'DEBUG: {prop} updated to value {val}')
		pass

	def doExport( self, path ):
		pass

	def onImageLoaded( self, name, img ):
		self.setProperty( 'Image'+name, img )

if __name__ == '__main__':
	app = q.QApplication()
	win = mainWin()
	win.show()
	app.exec()