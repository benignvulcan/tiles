
from PyQt5 import QtCore, QtGui, QtWidgets

class SpinSlider(QtWidgets.QWidget):
  '''A simple QSpinBox + QSlider control.
    The SpinBox is above or to the left of the slider.
  '''

  '''This perhaps should inherit from one of the two,
    but I may not support all those features.

    Features to consider supporting:
      setRange slot
      setOrientation slot
      orientation property
      SpinBox prefix & suffix properties
      rangeChanged signal
        Note that QAbstractSlider emits rangeChanged,
        but QSpinBox has no equivalent signal.
  '''

  valueChanged = QtCore.pyqtSignal(int, name='valueChanged')

  def __init__(self, orientation=QtCore.Qt.Horizontal, parent=None):
    super().__init__(parent)
    self._orientation = orientation
    self._init_ui()

  def _init_ui(self):
    if self._orientation == QtCore.Qt.Vertical:
      layout = QtWidgets.QVBoxLayout()
    else:
      layout = QtWidgets.QHBoxLayout()
    self.setLayout(layout)

    self.spinBox = QtWidgets.QSpinBox()
    self.slider = QtWidgets.QSlider(self._orientation)

    layout.addWidget(self.spinBox)

    Z = QtWidgets.QSizePolicy  # Fixed, Minimum, Maximum, Preferred, Expanding
    if self._orientation == QtCore.Qt.Vertical:
      layout.addWidget(self.slider, alignment=QtCore.Qt.AlignHCenter)
      self.setSizePolicy(Z.Preferred, Z.Expanding)
    else:
      layout.addWidget(self.slider)
      self.setSizePolicy(Z.Expanding, Z.Preferred)
    self.spinBox.setSizePolicy(Z.Preferred, Z.Fixed)

    self.spinBox.valueChanged.connect(self.setValue)
    self.slider.valueChanged.connect(self.setValue)

  def setMinimum(self, x):
    self.spinBox.setMinimum(x)
    self.slider.setMinimum(x)

  def minimum(self):
    return self.spinBox.minimum()

  def setMaximum(self, x):
    self.spinBox.setMaximum(x)
    self.slider.setMaximum(x)

  def maximum(self):
    return self.spinBox.maximum()

  def setValue(self, x):
    changed = False
    if x != self.spinBox.value():
      self.spinBox.setValue(x)
      changed = True
    if x != self.slider.value():
      self.slider.setValue(x)
      changed = True
    if changed:
      self.valueChanged.emit(x)

  def value(self):
    return self.spinBox.value()


if __name__=='__main__':
  import sys
  class TestApp(QtWidgets.QApplication):
    def __init__(self):
      orientation = QtCore.Qt.Horizontal
      if 'vertical' in sys.argv:
        orientation = QtCore.Qt.Vertical
        sys.argv.remove('vertical')
      super().__init__(sys.argv)
      self.ss = SpinSlider(orientation)
      self.ss.setWindowTitle('SpinSlider Test')
      self.ss.show()
      self.ss.valueChanged.connect(self.showValue)
      self.lastWindowClosed.connect(self.exitWithValue)
    def showValue(self, val):
      print('valueChanged: {}'.format(val), flush=True)
    @QtCore.pyqtSlot()
    def exitWithValue(self):
      self.exit(self.ss.value())
  sys.exit(TestApp().exec_())

