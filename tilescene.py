
import math
from PyQt5 import QtCore, QtGui, QtWidgets
import tileselection


class TileScene(QtWidgets.QGraphicsScene):

  RENDER_PLAIN = 0
  RENDER_OUTLINE = 1

  # A tile magnetically snapped - app might want to make a clicking sound
  snapped = QtCore.pyqtSignal()

  # One or more tiles permanantly changed their shape, transformation, color, existence, etc.
  tileChanged = QtCore.pyqtSignal()

  def __init__(self, logger, sceneRect=None, parent=None):
    self._log = logger
    #if sceneRect is None:
    #  QtWidgets.QGraphicsScene.__init__(self, parent)
    #else:
    #  QtWidgets.QGraphicsScene.__init__(self, sceneRect, parent)
    kwargs = { 'parent': parent }
    if not sceneRect is None: kwargs['sceneRect'] = sceneRect
    super().__init__(**kwargs)
    self.snapToTilesEnabled = True
    self.snapToAnglesEnabled = True
    #bSetExisting = self.setProperty("snapToTilesEnabled", True)
    #self._log.debug('bSetExisting = {}', bSetExisting)
    self.snapDist = .25
    self.renderMode = self.RENDER_PLAIN
    self.selectionGroup = tileselection.SelectionGroup(logger)
    self.addItem(self.selectionGroup)
    self.selectionGroup.setZValue(1) # everything else defaults to 0
    self.selectionGroup.setSelected(True)
    self.changed.connect(self.recalcSceneRect)
    self.marchingAntsOffset = 0
    #self.startTimer(500)

  @QtCore.pyqtSlot()
  def recalcSceneRect(self):
    # Force sceneRect to shrink, as well as grow.
    self.setSceneRect(self.itemsBoundingRect())

  def addItem(self, item, suppressChange=False):
    super().addItem(item)
    if not suppressChange:
      self.tileChanged.emit()

  def keepItem(self, item):
    assert item.scene() == self
    # Sometimes items disappear from the scene even though they're in the scene!
    self.removeItem(item)
    # Calling this without the above removeItem() generates a complaint,
    # but not calling it leaves the item disappeared.
    self.addItem(item, suppressChange=True)

  @QtCore.pyqtSlot()
  def clearSelection(self):
    self._log.trace('entering')
    for it in self.selectionGroup.childItems():
      assert not it is self.selectionGroup
      p0 = it.pos()
      flags0 = it.flags()
      self.selectionGroup.removeFromGroup(it)
      self.removeItem(it)
      self.addItem(it, suppressChange=True)
      it.setSelected(False)
      assert not it.scene() in (None,0)
      assert it.scene() is self
      #self._log.trace('pos: {} -> {}', p0, it.pos())
      if flags0 != it.flags():
        self._log.trace('flags: {} -> {}', flags0, it.flags())
    for it in self.items():
      if not it is self.selectionGroup and it.isSelected():
        self._log.warning('found selected item not in selectionGroup')
        it.setSelected(False)
    self._log.trace('returning')

  @QtCore.pyqtSlot()
  def removeSelection(self):
    'Remove all selected items from scene'
    changed = False
    for it in self.selectionGroup.childItems():
      assert not it is self.selectionGroup
      self.selectionGroup.removeFromGroup(it)
      self.removeItem(it)
      changed = True
    for it in self.selectedItems():
      if not it is self.selectionGroup:
        self._log.warning('found selected item not in selectionGroup')
        self.removeItem(it)
        changed = True
    if changed:
      self.selectionGroup.cancelDrag()
      self.tileChanged.emit()

  @QtCore.pyqtSlot()
  def setSelectionAll(self):
    for it in self.items():
      if it.isEnabled() and it.flags() & QtWidgets.QGraphicsItem.ItemIsSelectable and not it is self.selectionGroup:
        it.setSelected(True)
        self.selectionGroup.addToGroup(it)

  def timerEvent(self, _tEvt):
    self.marchingAntsOffset = (self.marchingAntsOffset+1) % 12
    self.selectionGroup.update()

  def drawBackground(self, painter, rect):
    super().drawBackground(painter, rect)
    if self._log.isEnabledFor('debug'):
      self.paintSceneRect(painter)

  def paintSceneRect(self, painter):
    r = self.sceneRect()
    painter.setPen(QtCore.Qt.NoPen)
    painter.setBrush(QtGui.QBrush(QtCore.Qt.gray))
    painter.drawRect(QtCore.QRectF(r.right(), r.top()+r.height()/100, r.width()/100, r.height()))
    painter.drawRect(QtCore.QRectF(r.left()+r.width()/100, r.bottom(), r.width(), r.height()/100))
    painter.setBrush(QtCore.Qt.NoBrush)
    painter.setPen(QtGui.QPen(QtCore.Qt.black, 0))
    painter.drawRect(r)

