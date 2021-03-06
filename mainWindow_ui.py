# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainWindow.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MagneticTilesMainWindow(object):
    def setupUi(self, MagneticTilesMainWindow):
        MagneticTilesMainWindow.setObjectName("MagneticTilesMainWindow")
        MagneticTilesMainWindow.resize(1024, 768)
        self.centralwidget = QtWidgets.QWidget(MagneticTilesMainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setContentsMargins(2, 2, 2, 2)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.graphicsView = TileView(self.centralwidget)
        self.graphicsView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.graphicsView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.graphicsView.setObjectName("graphicsView")
        self.horizontalLayout.addWidget(self.graphicsView)
        MagneticTilesMainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MagneticTilesMainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1024, 21))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuEdit = QtWidgets.QMenu(self.menubar)
        self.menuEdit.setObjectName("menuEdit")
        self.menuHelp = QtWidgets.QMenu(self.menubar)
        self.menuHelp.setObjectName("menuHelp")
        self.menuShape = QtWidgets.QMenu(self.menubar)
        self.menuShape.setObjectName("menuShape")
        self.menuAdd = QtWidgets.QMenu(self.menuShape)
        self.menuAdd.setToolTip("")
        self.menuAdd.setObjectName("menuAdd")
        self.menuView = QtWidgets.QMenu(self.menubar)
        self.menuView.setObjectName("menuView")
        MagneticTilesMainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MagneticTilesMainWindow)
        self.statusbar.setObjectName("statusbar")
        MagneticTilesMainWindow.setStatusBar(self.statusbar)
        self.actionE_xit = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionE_xit.setObjectName("actionE_xit")
        self.actionQuit = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionQuit.setObjectName("actionQuit")
        self.actionCopy = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionCopy.setObjectName("actionCopy")
        self.actionPaste = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionPaste.setObjectName("actionPaste")
        self.actionCut = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionCut.setObjectName("actionCut")
        self.actionDelete = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionDelete.setObjectName("actionDelete")
        self.actionSave = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionSave.setObjectName("actionSave")
        self.actionOpen = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionOpen.setObjectName("actionOpen")
        self.actionAbout = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionAbout.setMenuRole(QtWidgets.QAction.AboutRole)
        self.actionAbout.setObjectName("actionAbout")
        self.actionAboutQt = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionAboutQt.setMenuRole(QtWidgets.QAction.AboutQtRole)
        self.actionAboutQt.setObjectName("actionAboutQt")
        self.actionSelectAll = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionSelectAll.setObjectName("actionSelectAll")
        self.actionSaveAs = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionSaveAs.setObjectName("actionSaveAs")
        self.actionFileNew = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionFileNew.setObjectName("actionFileNew")
        self.actionStatusBar = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionStatusBar.setCheckable(True)
        self.actionStatusBar.setChecked(True)
        self.actionStatusBar.setObjectName("actionStatusBar")
        self.actionFullscreen = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionFullscreen.setCheckable(True)
        self.actionFullscreen.setObjectName("actionFullscreen")
        self.actionOutline = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionOutline.setCheckable(True)
        self.actionOutline.setObjectName("actionOutline")
        self.actionPrint = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionPrint.setObjectName("actionPrint")
        self.actionDebug = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionDebug.setCheckable(True)
        self.actionDebug.setObjectName("actionDebug")
        self.actionSnapObjects = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionSnapObjects.setCheckable(True)
        self.actionSnapObjects.setChecked(True)
        self.actionSnapObjects.setObjectName("actionSnapObjects")
        self.actionSnapSettings = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionSnapSettings.setObjectName("actionSnapSettings")
        self.actionSnapAngles = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionSnapAngles.setCheckable(True)
        self.actionSnapAngles.setChecked(True)
        self.actionSnapAngles.setObjectName("actionSnapAngles")
        self.actionShapeReset = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionShapeReset.setObjectName("actionShapeReset")
        self.actionViewReset = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionViewReset.setObjectName("actionViewReset")
        self.actionHelpHelp = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionHelpHelp.setObjectName("actionHelpHelp")
        self.actionTriangle = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionTriangle.setObjectName("actionTriangle")
        self.actionShapeMirror = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionShapeMirror.setObjectName("actionShapeMirror")
        self.actionDeselectAll = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionDeselectAll.setObjectName("actionDeselectAll")
        self.actionBackground_Color = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionBackground_Color.setObjectName("actionBackground_Color")
        self.actionBorder_Color = QtWidgets.QAction(MagneticTilesMainWindow)
        self.actionBorder_Color.setObjectName("actionBorder_Color")
        self.menuFile.addAction(self.actionFileNew)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionOpen)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionSave)
        self.menuFile.addAction(self.actionSaveAs)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionPrint)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionQuit)
        self.menuEdit.addAction(self.actionCut)
        self.menuEdit.addAction(self.actionCopy)
        self.menuEdit.addAction(self.actionPaste)
        self.menuEdit.addAction(self.actionDelete)
        self.menuEdit.addSeparator()
        self.menuEdit.addAction(self.actionSelectAll)
        self.menuEdit.addAction(self.actionDeselectAll)
        self.menuHelp.addAction(self.actionHelpHelp)
        self.menuHelp.addSeparator()
        self.menuHelp.addAction(self.actionAboutQt)
        self.menuHelp.addAction(self.actionAbout)
        self.menuShape.addAction(self.menuAdd.menuAction())
        self.menuShape.addSeparator()
        self.menuShape.addAction(self.actionShapeMirror)
        self.menuShape.addAction(self.actionShapeReset)
        self.menuView.addAction(self.actionSnapObjects)
        self.menuView.addAction(self.actionSnapAngles)
        self.menuView.addAction(self.actionSnapSettings)
        self.menuView.addSeparator()
        self.menuView.addAction(self.actionViewReset)
        self.menuView.addAction(self.actionOutline)
        self.menuView.addAction(self.actionBackground_Color)
        self.menuView.addAction(self.actionBorder_Color)
        self.menuView.addSeparator()
        self.menuView.addAction(self.actionStatusBar)
        self.menuView.addAction(self.actionFullscreen)
        self.menuView.addAction(self.actionDebug)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())
        self.menubar.addAction(self.menuShape.menuAction())
        self.menubar.addAction(self.menuView.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        self.retranslateUi(MagneticTilesMainWindow)
        self.actionQuit.triggered.connect(MagneticTilesMainWindow.close)
        self.actionStatusBar.toggled['bool'].connect(self.statusbar.setVisible)
        QtCore.QMetaObject.connectSlotsByName(MagneticTilesMainWindow)

    def retranslateUi(self, MagneticTilesMainWindow):
        _translate = QtCore.QCoreApplication.translate
        MagneticTilesMainWindow.setWindowTitle(_translate("MagneticTilesMainWindow", "Magnetic Tiles"))
        self.menuFile.setTitle(_translate("MagneticTilesMainWindow", "&File"))
        self.menuEdit.setTitle(_translate("MagneticTilesMainWindow", "&Edit"))
        self.menuHelp.setTitle(_translate("MagneticTilesMainWindow", "&Help"))
        self.menuShape.setTitle(_translate("MagneticTilesMainWindow", "&Shape"))
        self.menuAdd.setStatusTip(_translate("MagneticTilesMainWindow", "Create another tile"))
        self.menuAdd.setTitle(_translate("MagneticTilesMainWindow", "&Add"))
        self.menuView.setTitle(_translate("MagneticTilesMainWindow", "&View"))
        self.actionE_xit.setText(_translate("MagneticTilesMainWindow", "&Quit"))
        self.actionQuit.setText(_translate("MagneticTilesMainWindow", "&Quit"))
        self.actionQuit.setStatusTip(_translate("MagneticTilesMainWindow", "Exit this program"))
        self.actionQuit.setShortcut(_translate("MagneticTilesMainWindow", "Ctrl+Q"))
        self.actionCopy.setText(_translate("MagneticTilesMainWindow", "&Copy"))
        self.actionCopy.setStatusTip(_translate("MagneticTilesMainWindow", "Copy the selection to the clipboard"))
        self.actionCopy.setShortcut(_translate("MagneticTilesMainWindow", "Ctrl+C"))
        self.actionPaste.setText(_translate("MagneticTilesMainWindow", "&Paste"))
        self.actionPaste.setStatusTip(_translate("MagneticTilesMainWindow", "Paste from the clipboard"))
        self.actionPaste.setShortcut(_translate("MagneticTilesMainWindow", "Ctrl+V"))
        self.actionCut.setText(_translate("MagneticTilesMainWindow", "C&ut"))
        self.actionCut.setStatusTip(_translate("MagneticTilesMainWindow", "Cut the selection to the clipboard"))
        self.actionCut.setShortcut(_translate("MagneticTilesMainWindow", "Ctrl+X"))
        self.actionDelete.setText(_translate("MagneticTilesMainWindow", "&Delete"))
        self.actionDelete.setStatusTip(_translate("MagneticTilesMainWindow", "Delete the selection"))
        self.actionDelete.setShortcut(_translate("MagneticTilesMainWindow", "Del"))
        self.actionSave.setText(_translate("MagneticTilesMainWindow", "&Save..."))
        self.actionSave.setStatusTip(_translate("MagneticTilesMainWindow", "Save your work"))
        self.actionSave.setShortcut(_translate("MagneticTilesMainWindow", "Ctrl+S"))
        self.actionOpen.setText(_translate("MagneticTilesMainWindow", "&Open..."))
        self.actionOpen.setStatusTip(_translate("MagneticTilesMainWindow", "Open a file of previously saved work"))
        self.actionOpen.setShortcut(_translate("MagneticTilesMainWindow", "Ctrl+O"))
        self.actionAbout.setText(_translate("MagneticTilesMainWindow", "&About Tiles..."))
        self.actionAbout.setStatusTip(_translate("MagneticTilesMainWindow", "Version and copyright information"))
        self.actionAboutQt.setText(_translate("MagneticTilesMainWindow", "About &Qt..."))
        self.actionAboutQt.setStatusTip(_translate("MagneticTilesMainWindow", "Qt information"))
        self.actionSelectAll.setText(_translate("MagneticTilesMainWindow", "Select &All"))
        self.actionSelectAll.setStatusTip(_translate("MagneticTilesMainWindow", "Select all objects"))
        self.actionSelectAll.setShortcut(_translate("MagneticTilesMainWindow", "Ctrl+A"))
        self.actionSaveAs.setText(_translate("MagneticTilesMainWindow", "Save &As..."))
        self.actionSaveAs.setStatusTip(_translate("MagneticTilesMainWindow", "Save your work with a new name"))
        self.actionSaveAs.setShortcut(_translate("MagneticTilesMainWindow", "Ctrl+Shift+S"))
        self.actionFileNew.setText(_translate("MagneticTilesMainWindow", "&New..."))
        self.actionFileNew.setStatusTip(_translate("MagneticTilesMainWindow", "Start a new empty scene"))
        self.actionStatusBar.setText(_translate("MagneticTilesMainWindow", "Status &Bar"))
        self.actionStatusBar.setStatusTip(_translate("MagneticTilesMainWindow", "Toggle display of this status bar"))
        self.actionFullscreen.setText(_translate("MagneticTilesMainWindow", "&Fullscreen"))
        self.actionFullscreen.setStatusTip(_translate("MagneticTilesMainWindow", "Toggle full-screen mode"))
        self.actionFullscreen.setShortcut(_translate("MagneticTilesMainWindow", "F11"))
        self.actionOutline.setText(_translate("MagneticTilesMainWindow", "&Outline"))
        self.actionOutline.setStatusTip(_translate("MagneticTilesMainWindow", "Toggle outline display mode"))
        self.actionOutline.setShortcut(_translate("MagneticTilesMainWindow", "O"))
        self.actionPrint.setText(_translate("MagneticTilesMainWindow", "&Print..."))
        self.actionDebug.setText(_translate("MagneticTilesMainWindow", "&Debug"))
        self.actionDebug.setStatusTip(_translate("MagneticTilesMainWindow", "Toggle debugging mode"))
        self.actionSnapObjects.setText(_translate("MagneticTilesMainWindow", "Snap to &Shapes"))
        self.actionSnapObjects.setStatusTip(_translate("MagneticTilesMainWindow", "Toggle magnetic snapping to other shapes"))
        self.actionSnapSettings.setText(_translate("MagneticTilesMainWindow", "Snap Se&ttings..."))
        self.actionSnapSettings.setStatusTip(_translate("MagneticTilesMainWindow", "Set snapping distance and angle"))
        self.actionSnapAngles.setText(_translate("MagneticTilesMainWindow", "Snap to &Angles"))
        self.actionSnapAngles.setStatusTip(_translate("MagneticTilesMainWindow", "Toggle rotating to only nice angles"))
        self.actionShapeReset.setText(_translate("MagneticTilesMainWindow", "&Reset"))
        self.actionShapeReset.setStatusTip(_translate("MagneticTilesMainWindow", "Restore selected shapes to base position, size, and orientation"))
        self.actionViewReset.setText(_translate("MagneticTilesMainWindow", "&Reset"))
        self.actionViewReset.setStatusTip(_translate("MagneticTilesMainWindow", "Reset view to default size, orientation, and position"))
        self.actionHelpHelp.setText(_translate("MagneticTilesMainWindow", "&Help"))
        self.actionHelpHelp.setStatusTip(_translate("MagneticTilesMainWindow", "Display documentation"))
        self.actionTriangle.setText(_translate("MagneticTilesMainWindow", "Triangle"))
        self.actionShapeMirror.setText(_translate("MagneticTilesMainWindow", "&Mirror"))
        self.actionShapeMirror.setStatusTip(_translate("MagneticTilesMainWindow", "Flip shape horizontally"))
        self.actionShapeMirror.setShortcut(_translate("MagneticTilesMainWindow", "M"))
        self.actionDeselectAll.setText(_translate("MagneticTilesMainWindow", "D&eselect All"))
        self.actionDeselectAll.setStatusTip(_translate("MagneticTilesMainWindow", "Un-select all objects"))
        self.actionBackground_Color.setText(_translate("MagneticTilesMainWindow", "Background Color..."))
        self.actionBackground_Color.setStatusTip(_translate("MagneticTilesMainWindow", "Change background color"))
        self.actionBorder_Color.setText(_translate("MagneticTilesMainWindow", "Border Color..."))
        self.actionBorder_Color.setStatusTip(_translate("MagneticTilesMainWindow", "Change border color of tiles"))

from tileview import TileView
