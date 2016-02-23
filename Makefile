#!/usr/bin/make
# GNU Makefile

all: mainWindow_ui.py

mainWindow_ui.py: mainWindow.ui
	pyuic5 -o mainWindow_ui.py mainWindow.ui

test:
	./qmathturtle.py

clean:
	rm -f *.pyc *.pyo
	rm -rf __pycache__/