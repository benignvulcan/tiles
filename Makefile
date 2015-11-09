#!/usr/bin/make
# GNU Makefile

all: mainWindow_ui.py

mainWindow_ui.py: mainWindow.ui
	pyuic4 -o mainWindow_ui.py mainWindow.ui

clean:
	rm -f *.pyc *.pyo

