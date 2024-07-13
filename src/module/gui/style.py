STYLESHEET_TILE_REQUIRED = '''
border-color: #999;
'''

STYLESHEET_MIN = '''
QLabel#hint {
	color: #777;
	font-size: 10px;
	font-weight: normal;
}
'''

STYLESHEET = STYLESHEET_MIN + '''
QMainWindow {
	background-color: #272727;
}

* {
	font-size: 12px;
	font-weight: 350;
	color: #ccc;
}

QGroupBox {
	background-color: #333;
	border: none;
	margin-top: 18px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
	color: #999;
}

QLineEdit {
	font-weight: normal;
}

QToolButton {
	border: 1px solid #555;
	background-color: #333;
}

QToolButton:hover {
	border-color: #666;
	background-color: #444;
}

QToolButton:pressed {
	background-color: #333;
}

QLineEdit:disabled {
	background-color: #333;
	border: 1px solid #272727;
	color: #888;
}

QPushButton {
	border: 1px solid #666;
	padding: 5px 15px;
	background-color: #444;
	color: #ddd;
}

QPushButton:hover {
	background-color: #666;
	color: #eee;
}

QPushButton:pressed {
	background-color: #333;
	color: #ddd;
}

QProgressBar {
    border: 1px solid #333;
	background-color: #282828;
    border-radius: 0px;
}

QProgressBar::chunk {
    background-color: #2471b5;
}
'''
