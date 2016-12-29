#!/usr/bin/env python3

import math
from PyQt5 import QtCore, QtGui, QtWidgets

UNIT_LINE = QtCore.QLineF( 0.0,0.0, 1.0,0.0 )

def GetScaleRotation(xform):
  "Given a QTransform, return it's scaling factor and rotation angle (0-360 degrees)"
  assert xform.type() < QtGui.QTransform.TxShear
  xline = xform.map(UNIT_LINE)
  return (xline.length(), xline.angle())

class TileView(QtWidgets.QGraphicsView):
  "A QGraphicsView that can be panned, rolled, and zoomed by the user."

  # constants for different dragging states
  DRAG_NONE   = 0
  DRAG_PAN    = 1
  DRAG_ROLL   = 2
  DRAG_ZOOM   = 3 # or DOLLY
  DRAG_SELECT = 4

  def __init__(self, parent):
    super().__init__(parent=parent)
    self.resetTransformPy()
    self._angular_resolution = 120  # foldl1 lcm [3,4,5,6,8]
    #self.dragMode = QtWidgets.QGraphicsView.ScrollHandDrag  # what to do wtih mouse clicks not caught by a GraphicsItem
    self._drag_type = self.DRAG_NONE
    self._drag_start_pos = None
    self._rubberBandItem = QtWidgets.QGraphicsPolygonItem()
    self._rubberBandItem.setZValue(2)
    self._rubberBandItem.setBrush(QtGui.QBrush(QtGui.QColor(255,255,0,31)))
    self._rubberBandItem.setPen(QtGui.QPen(QtCore.Qt.black, 0, QtCore.Qt.DashLine))
    self._rubberBandItem.hide()
    #self.scene().addItem(self._rubberBandItem)
    self.setRenderHints(self.renderHints() | QtGui.QPainter.Antialiasing)
    #self.setRubberBandSelectionMode(QtCore.Qt.ContainsItemShape)
    self.setMouseTracking(True)
    self.setAcceptDrops(True)
    self._log = None

  def setScene(self, scene):
    super().setScene(scene)
    self.scene().addItem(self._rubberBandItem)

  def resetTransformPy(self):
    "Reset transform to the default for this application."
    # Note that most C++ members of QGraphicsView are not virtual, and so can't be overridden.
    self.resetTransform()
    self.translate(.5,.5) # avoid stupid antialiased-orthogonal-black-lines-become-two-gray-pixels-thick problem.
    self.ZoomRel(32)      # Unit square defaults to 32 px square view
    self.centerOn(0,0)    # QABstractScrollArea's panning overrides the QGraphicsView's transform translation.

  ZOOM_FACTOR=math.sqrt(2)

  def ZoomRel(self, f=1.0):
    z = self.transform().map(UNIT_LINE).length() * f
    if z > .001 and z < 10000:
      self.scale(f,f)
  def ZoomIn(self):
    self.ZoomRel(self.ZOOM_FACTOR)
  def ZoomOut(self):
    self.ZoomRel(1/self.ZOOM_FACTOR)

  def RollRelDeg(self, r=0):
    self.rotate(r)

  def wheelEvent(self, mouseEvt):
    #self._log.trace("wheelEvent.delta() = {}", mouseEvt.delta() / 8.0)
    f = self.ZOOM_FACTOR ** (mouseEvt.angleDelta().y() / 120.0)  # 120 = 15 degrees = 1 typical wheel step
    self.ZoomRel(f)

  def startXformDrag(self, mouseEvt, drag_type):
    'Start dragging a transformation of the view'
    if drag_type == self.DRAG_NONE: return
    self._drag_type = drag_type
    self._drag_start_xform = self.transform()
    self._drag_start_scrollValues = (self.horizontalScrollBar().value(), self.verticalScrollBar().value())
    self._drag_start_pos = mouseEvt.pos()
    self._drag_start_vector = QtCore.QLineF(self.rect().center(), self._drag_start_pos)
    self.setCursor(QtCore.Qt.ClosedHandCursor)
  def updateXformDrag(self, mouseEvt):
    invert_snap = bool(mouseEvt.modifiers() & QtCore.Qt.ControlModifier)
    if self._drag_type == self.DRAG_PAN:
      offset = mouseEvt.pos() - self._drag_start_pos
      self.horizontalScrollBar().setValue(self._drag_start_scrollValues[0] - offset.x())
      self.verticalScrollBar().setValue(self._drag_start_scrollValues[1] - offset.y())
    elif self._drag_type == self.DRAG_ROLL:
      move_vector = QtCore.QLineF(self.rect().center(), mouseEvt.pos())
      theta = move_vector.angleTo(self._drag_start_vector)
      if invert_snap != self.scene().snapToAnglesEnabled:
        q = 360.0 / self._angular_resolution
        theta = q * round(float(theta) / q)
      self.setTransform(QtGui.QTransform(self._drag_start_xform).rotate(theta))
      self._log.trace('theta= {}', theta)
  def cancelXformDrag(self):
    if self._drag_type == self.DRAG_ROLL:
      self.setTransform(QtGui.QTransform(self._drag_start_xform))
    self.setCursor(QtCore.Qt.ArrowCursor)
    self._drag_type = self.DRAG_NONE

  def startSelectDrag(self, mouseEvt):
    self._drag_type = self.DRAG_SELECT
    self._drag_start_pos = mouseEvt.pos()
    self._preexistingSelection = self.scene().selectionGroup.childItems()
    self._log.trace("{} pre-existing selections", len(self._preexistingSelection))
    self._rubberBandItem.setPolygon(QtGui.QPolygonF())
    self._rubberBandItem.show()
  def updateSelectDrag(self, mouseEvt):
    viewIntRect = QtCore.QRect(self._drag_start_pos, mouseEvt.pos()).normalized()
    #if rectangle has in fact changed: #TODO
    #emit rubberBandChanged ?
    poly = self._rubberBandItem.mapFromScene(self.mapToScene(viewIntRect))
    #self._log.trace('rubberBandItem.setPolygon({})', poly)
    self._rubberBandItem.setPolygon(poly)
    #self.scene().setSelectionArea(selectionPath, self.viewportTransform())
    rubberBandedItems = []
    for it in self.scene().items(poly, deviceTransform=self.viewportTransform()):
      if (    not it is self.scene().selectionGroup
          and it.isEnabled()
          and it.flags() & QtWidgets.QGraphicsItem.ItemIsSelectable):
        rubberBandedItems.append(it)
        if not it.isSelected():
          it.setSelected(True)
    if rubberBandedItems:
      self._log.trace("{} items intersect rubberBand", len(rubberBandedItems))
    deselectedItems = []
    for it in self.scene().selectionGroup.childItems():
      assert not it is self.scene().selectionGroup
      if not (it in rubberBandedItems or it in self._preexistingSelection):
        #if not it.collidesWithItem(self._rubberBandItem): # redundant
          it.setSelected(False)
          deselectedItems.append(it)
    if deselectedItems:
      self._log.trace("{} items removed from rubberBand", len(deselectedItems))
  def stopSelectDrag(self, mouseEvt):
    self._drag_type = self.DRAG_NONE
    self._rubberBandItem.hide()
    self.update()

  def mousePressEvent(self, mouseEvt):
    if self.scene().mouseGrabberItem():
      self._log.trace("mouse grabbed: passing to super()")
      return super().mousePressEvent(mouseEvt)
    items = self.items(mouseEvt.pos())
    for it in items:
      if it.isEnabled() and it.flags() & QtWidgets.QGraphicsItem.ItemIsSelectable:
        # Use overridden parent to do standard event multiplexing to scene's QGraphicsItems:
        self._log.trace("item found: passing to super()")
        return super().mousePressEvent(mouseEvt)
    #if mouseEvt.isAccepted():
    # # Parent mousePressEvent found a QGraphicsItem to handle this mouseEvt.
    # return
    # Now handle everything else: User is trying to mouse on background.
    self._log.trace("mouse event not handled by any QGraphicsItem")
    if mouseEvt.button() == QtCore.Qt.LeftButton:
      if not (mouseEvt.modifiers() & QtCore.Qt.ShiftModifier):
        self._log.trace("deselecting all")
        #self.scene().selectionGroup.setSelected(False)
        self.scene().clearSelection()
      mouseEvt.accept()
      return self.startSelectDrag(mouseEvt)
      # Only left button should rubber-band, so only enable RubberBandDrag
      #   while left button is pressed.
      self.setDragMode(self.RubberBandDrag)
      #assert self.rubberBandSelectionMode() == QtCore.Qt.ContainsItemShape
      self.setRubberBandSelectionMode(QtCore.Qt.IntersectsItemShape)
      # Reprocess this mouse event with rubber-band drag now enabled.
      # The scene shouldn't know the difference between this and a new event.
      self._log.trace("rubber band dragging: passing to super()")
      super().mousePressEvent(mouseEvt)
    elif mouseEvt.button() == QtCore.Qt.MidButton:
      # Middle button pans scene
      self.startXformDrag(mouseEvt, self.DRAG_PAN)
      mouseEvt.accept()
    elif mouseEvt.button() == QtCore.Qt.RightButton:
      self.startXformDrag(mouseEvt, self.DRAG_ROLL)
      mouseEvt.accept()
    # Ignore other buttons
  def mouseMoveEvent(self, mouseEvt):
    if self._drag_type == self.DRAG_SELECT:
      self.updateSelectDrag(mouseEvt)
      mouseEvt.accept()
    elif self._drag_type != self.DRAG_NONE:
      self.updateXformDrag(mouseEvt)
      mouseEvt.accept()
    else:
      super().mouseMoveEvent(mouseEvt)
  def mouseReleaseEvent(self, mouseEvt):
    if self._drag_type == self.DRAG_SELECT:
      self.stopSelectDrag(mouseEvt)
      mouseEvt.accept()
    elif self._drag_type != self.DRAG_NONE:
      self._drag_type = self.DRAG_NONE
      self.setCursor(QtCore.Qt.ArrowCursor)
      mouseEvt.accept()
    else:
      super().mouseReleaseEvent(mouseEvt)
      # Set NoDrag after all mousing handled by QGraphicsView.
      self.setDragMode(self.NoDrag)

  def dragEnterEvent(self, dragEnterEvt):
    self._log.debug('{}', [s for s in dragEnterEvt.mimeData().formats()])
    if dragEnterEvt.mimeData().hasFormat(MIME_TYPE_SVG):
      dragEnterEvt.accept()
  #def dragMoveEvent(self, dragMoveEvt): pass
  def dropEvent(self, dropEvt):
    self._log.debug()
    dropEvt.acceptProposedAction()

  def focusOutEvent(self, evt):
    self.cancelXformDrag()
    self.scene().selectionGroup.cancelDrag()

  def keyPressEvent(self, keyEvt):
    # TODO? call setFocusPolicy()

    # keyEvt.isAccepted() is True by default; pass keyEvt to superclass to "ignore".
    # Pass to QGraphicsView which:
    #   1) Passes it to QGraphicsScene which:
    #     * Processes tab and backtab
    #     * Passes it to focus item(s)
    #   2) Passes it to QAbstractScrollArea which:
    #     * processes arrows & pgup/dn.
    #     * or calls keyEvt.ignore()
    super().keyPressEvent(keyEvt) # sets keyEvt.isAccepted() if key is handled
    k = keyEvt.key()
    # Whether or not Esc was processed by scene/QAbstractScrollArea,
    #   also process it here.
    if   k == QtCore.Qt.Key_Escape:
      if self._drag_type != self.DRAG_NONE:
        self.cancelXformDrag()
      elif len(self.scene().selectionGroup.childItems()):
        if not keyEvt.isAccepted():
          self.scene().clearSelection()
          keyEvt.accept()
    if not keyEvt.isAccepted():
      if   k == QtCore.Qt.Key_Plus : self.ZoomIn()
      elif k == QtCore.Qt.Key_Minus: self.ZoomOut()
      elif k == QtCore.Qt.Key_BracketLeft  or k == QtCore.Qt.Key_Slash   : self.RollRelDeg(-15)
      elif k == QtCore.Qt.Key_BracketRight or k == QtCore.Qt.Key_Asterisk: self.RollRelDeg( 15)
      else: return # not recgonized, leave keyEvt as ignored
      keyEvt.accept()
