import os
import compileall
from shutil import copyfile

home = os.path.expanduser("~")
plugin_folder =  home + "\.qgis2\python\plugins\geoserverexplorer"
current_dir = os.getcwd() + '\\files'

files = []
files.append({'name': '\\catalog.py', 'dest': '\\qgis'})
files.append({'name': '\\gsoperations.py', 'dest': '\\gui'})
files.append({'name': '\\layerdialog.py', 'dest': '\\gui\\dialogs'})

for file in files:
    copyfile(current_dir + file['name'], plugin_folder + file['dest'] + file['name'])
	
compileall.compile_dir(plugin_folder, force=True)



