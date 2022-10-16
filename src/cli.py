if __name__ != '__main__':
	print( 'CLI cannot be run as module!' )
	exit(1)

import core
from argparse import ArgumentParser


parser = ArgumentParser( 'PBR-2-Source CLI', description='(BETA) A command line interface for PBR-2-Source.' )
parser.add_argument( 'source', dest='src' )
parser.add_argument( '--target', dest='target', default=None, help='The output directory for materials. If none is provided, it will default to the source directory.' )
parser.add_argument( '--mode', default='substance', help='What patterns the program should use to search for the texture files.', dest='mode' )
parser.add_argument( '--preset', default='default', help='What preset the program should use to determine the output parameters.', dest='preset' )
parser.add_argument( '--onlyvmt', action='store_true', help='Only generates the vmt.' )
parser.add_argument( '--onlytex', action='store_true', help='Only generates the vtfs.' )