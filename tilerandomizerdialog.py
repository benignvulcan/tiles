
from PyQt5 import QtCore, QtGui, QtWidgets

import spinslider

class TileRandomizerDialog(QtWidgets.QDialog):

  'Present the user with controls for specifying various kinds and amounts of randomization.'

  hsvApply = QtCore.pyqtSignal(int,int,int,int,name='hsvApply')
  rgbApply = QtCore.pyqtSignal(int,int,int,int,name='rgbApply')

  def __init__(self, parent):
    super().__init__(parent)
    self.init_ui()

  def init_ui(self):
    self.setObjectName('TileRandomizerDialog')
    self.setWindowTitle('Randomize Tiles')

    topLayout = QtWidgets.QVBoxLayout()
    self.setLayout(topLayout)

    self.tabWidget = QtWidgets.QTabWidget()
    topLayout.addWidget(self.tabWidget)

    self.add_tab(self.hsv_specs)
    self.add_tab(self.rgb_specs)

    bbflags = QtWidgets.QDialogButtonBox.Apply | QtWidgets.QDialogButtonBox.Close
    self.buttonBox = QtWidgets.QDialogButtonBox(bbflags, QtCore.Qt.Horizontal)
    self.buttonBox.setObjectName('buttonBox')
    topLayout.addWidget(self.buttonBox)

    self.buttonBox.rejected.connect(self.close)
    #self.buttonBox.clicked.connect(self.on_buttonBox_clicked)

    # Automagically connect signals from child objects to methods in self
    # with names of the form 'on_{object name}_{signal_name}'.
    QtCore.QMetaObject.connectSlotsByName(self)

  hsv_specs = [ 'hsv', 'Colors (HSV)', ('Hue', 359), ('Saturation', 255), ('Value', 255), ('Alpha', 255) ]
  rgb_specs = [ 'rgb', 'Colors (RGB)', ('Red', 255), ('Green', 255), ('Blue', 255), ('Alpha', 255) ]

  def add_tab(self, specs):
    tab = QtWidgets.QWidget()
    tabname = specs[0]
    tab.setObjectName(tabname+'_tab')
    layout = QtWidgets.QFormLayout()
    tab.setLayout(layout)
    for name, x in specs[2:]:
      aLabel, aSpinSlider = self.create_labeled_spinslider(tabname+'_'+name.lower(), 0, x)
      layout.addRow(aLabel, aSpinSlider)
    self.tabWidget.addTab(tab, specs[1])

  def create_labeled_spinslider(self, name, minVal, maxVal):
    aLabel = QtWidgets.QLabel(name)
    aLabel.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
    aSpinSlider = spinslider.SpinSlider()
    aSpinSlider.setObjectName('{}_spinslider'.format(name))
    aSpinSlider.setMinimum(minVal)
    aSpinSlider.setMaximum(maxVal)
    return (aLabel, aSpinSlider)

  def on_buttonBox_clicked(self, btn):
    if btn == self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply):
      tabname = self.tabWidget.currentWidget().objectName()
      if tabname == 'hsv_tab':
        h = self.findChild(spinslider.SpinSlider, 'hsv_hue_spinslider').value()
        s = self.findChild(spinslider.SpinSlider, 'hsv_saturation_spinslider').value()
        v = self.findChild(spinslider.SpinSlider, 'hsv_value_spinslider').value()
        a = self.findChild(spinslider.SpinSlider, 'hsv_alpha_spinslider').value()
        self.hsvApply.emit(h,s,v,a)
      elif tabname == 'rgb_tab':
        r = self.findChild(spinslider.SpinSlider, 'rgb_red_spinslider').value()
        g = self.findChild(spinslider.SpinSlider, 'rgb_green_spinslider').value()
        b = self.findChild(spinslider.SpinSlider, 'rgb_blue_spinslider').value()
        a = self.findChild(spinslider.SpinSlider, 'rgb_alpha_spinslider').value()
        self.rgbApply.emit(r,g,b,a)


