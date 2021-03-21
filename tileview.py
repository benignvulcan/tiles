
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
    self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
    self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
    self.setMouseTracking(True)
    self.setAcceptDrops(True)
    self._log = None

  def setScene(self, scene):
    super().setScene(scene)
    self.scene().addItem(self._rubberBandItem)
    self.scene().sceneRectChanged.connect(self.updateSceneRect)

  def updateSceneRect(self, rect):
    'Update the scrollable area to be about 3 times bigger than the scene.'
    self.setSceneRect(rect + QtCore.QMarginsF(rect.width(), rect.height(), rect.width(), rect.height()))

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
    'Start dragging a transformation of the view.'
    if drag_type == self.DRAG_NONE: return
    self._drag_type = drag_type
    self._drag_start_xform = self.transform()
    self._drag_start_scrollValues = (self.horizontalScrollBar().value(), self.verticalScrollBar().value())
    self._drag_start_pos = mouseEvt.pos()
    self._drag_start_vector = QtCore.QLineF(self.rect().center(), self._drag_start_pos)
    self.setCursor(QtCore.Qt.ClosedHandCursor)

  def updateXformDrag(self, mouseEvt):
    'Continue dragging a transformation of the view.'
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

  def stopXformDrag(self):
    'Finish dragging a transformation of the view, keeping the changes.'
    self.setCursor(QtCore.Qt.ArrowCursor)
    self._drag_type = self.DRAG_NONE

  def cancelXformDrag(self):
    'Abort dragging a transformation of the view, reverting to what it was.'
    self.setTransform(QtGui.QTransform(self._drag_start_xform))
    self.stopXformDrag()

  def startSelectDrag(self, mouseEvt):
    'Start dragging a selection rectangle.'
    self._drag_type = self.DRAG_SELECT
    self._drag_start_pos = mouseEvt.pos()
    self._preexistingSelection = self.scene().selectionGroup.childItems()
    self._log.trace("{} pre-existing selections", len(self._preexistingSelection))
    self._rubberBandItem.setPolygon(QtGui.QPolygonF())
    self._rubberBandItem.show()

  def updateSelectDrag(self, mouseEvt):
    'Continue dragging the selection rectangle.'
    viewIntRect = QtCore.QRect(self._drag_start_pos, mouseEvt.pos()).normalized()
    #if rectangle has in fact changed: #TODO
    #emit rubberBandChanged ?
    poly = self._rubberBandItem.mapFromScene(self.mapToScene(viewIntRect))
    self._rubberBandItem.setPolygon(poly)
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
    'Finish dragging the selection rectangle, keeping the selection.'
    self._drag_type = self.DRAG_NONE
    self._rubberBandItem.hide()
    self.update()

  def cancelSelectDrag(self, mouseEvt):
    'Abort dragging the selection rectangle, reverting the the prior selection.'
    for it in self.scene().selectionGroup.childItems():
      if not it in self._preexistingSelection:
        it.setSelected(False)
    self.stopSelectDrag(mouseEvt)

  def stopDrag(self, mouseEvt):
    'Finish (and keep) whatever kind of dragging may be happening.'
    if self._drag_type == self.DRAG_SELECT:
      self.stopSelectDrag(None)
    elif self._drag_type != self.DRAG_NONE:
      self.stopXformDrag()

  def cancelDrag(self, mouseEvt):
    'Cancel (and revert) whatever kind of dragging may be happening.'
    if self._drag_type == self.DRAG_SELECT:
      self.cancelSelectDrag(None)
    elif self._drag_type != self.DRAG_NONE:
      self.cancelXformDrag()

  def mapDragButton(self, button):
    if   button == QtCore.Qt.LeftButton  : return self.DRAG_SELECT
    elif button == QtCore.Qt.RightButton : return self.DRAG_ROLL
    elif button == QtCore.Qt.MiddleButton: return self.DRAG_PAN
    else: return self.DRAG_NONE

  def mousePressEvent(self, mouseEvt):
    if self.scene().mouseGrabberItem():
      # A tile has grabbed the mouse (to implement dragging without holding the button down).
      self._log.trace("mouse grabbed: passing to super()")
      # Do standard QGraphicsView event multiplexing to scene's QGraphicsItem:
      return super().mousePressEvent(mouseEvt)
    items = self.items(mouseEvt.pos())
    for it in items:
      if it.isEnabled() and it.flags() & QtWidgets.QGraphicsItem.ItemIsSelectable:
        # Do standard QGraphicsView event multiplexing to scene's QGraphicsItems:
        self._log.trace("item found: passing to super()")
        return super().mousePressEvent(mouseEvt)
    # It does not appear that this event should be propagated to a tile.
    # So it would seem user is trying to mouse on the background.
    # Start selecting, paning, or rotating.
    self._log.trace("mouse event not handled by any QGraphicsItem")
    if self._drag_type != self.DRAG_NONE:
      return
    drag_type = self.mapDragButton(mouseEvt.button())
    if drag_type == self.DRAG_SELECT:
      if not (mouseEvt.modifiers() & QtCore.Qt.ShiftModifier):
        self._log.trace("deselecting all")
        #self.scene().selectionGroup.setSelected(False)
        self.scene().clearSelection()
      mouseEvt.accept()
      return self.startSelectDrag(mouseEvt)
    elif drag_type == self.DRAG_PAN:
      self.startXformDrag(mouseEvt, drag_type)
      mouseEvt.accept()
    elif drag_type == self.DRAG_ROLL:
      self.startXformDrag(mouseEvt, drag_type)
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
    drag_type = self.mapDragButton(mouseEvt.button())
    if drag_type == self._drag_type:
      if self._drag_type == self.DRAG_SELECT:
        self.stopSelectDrag(mouseEvt)
        mouseEvt.accept()
        return
      elif self._drag_type != self.DRAG_NONE:
        self._drag_type = self.DRAG_NONE
        self.setCursor(QtCore.Qt.ArrowCursor)
        mouseEvt.accept()
        return
    super().mouseReleaseEvent(mouseEvt)

  def dragEnterEvent(self, dragEnterEvt):
    self._log.debug('{}', [s for s in dragEnterEvt.mimeData().formats()])
    if dragEnterEvt.mimeData().hasFormat("image/svg+xml"):
      dragEnterEvt.accept()

  def dropEvent(self, dropEvt):
    self._log.debug()
    dropEvt.acceptProposedAction()

  def focusOutEvent(self, evt):
    self.cancelDrag(None)
    self.scene().selectionGroup.cancelDrag()

  def keyPressEvent(self, keyEvt):
    # TODO? call setFocusPolicy()

    # keyEvt.isAccepted() is True by default; pass keyEvt to superclass if not acting on it.
    # Pass the event to QGraphicsView which:
    #   1) Passes it to QGraphicsScene which:
    #     * Processes tab and backtab
    #     * Passes it to focus item(s)
    #   2) Passes it to QAbstractScrollArea which:
    #     * processes arrows & pgup/dn.
    #     * or calls keyEvt.ignore()

    super().keyPressEvent(keyEvt)
    k = keyEvt.key()
    # Whether or not Esc is processed by scene/QAbstractScrollArea,
    #   also process it here.
    if k == QtCore.Qt.Key_Escape:
      if self._drag_type != self.DRAG_NONE:
        self.cancelDrag(None)
      elif len(self.scene().selectionGroup.childItems()):
        if not keyEvt.isAccepted():
          self.scene().clearSelection()
      else:
        self.resetTransformPy()
      keyEvt.accept()
      return
    if not keyEvt.isAccepted():
      if k == QtCore.Qt.Key_Plus:
        self.ZoomIn()
        keyEvt.accept()
        return
      elif k == QtCore.Qt.Key_Minus:
        self.ZoomOut()
        keyEvt.accept()
        return
      elif k == QtCore.Qt.Key_BracketLeft  or k == QtCore.Qt.Key_Slash:
        self.RollRelDeg(-15)
        keyEvt.accept()
        return
      elif k == QtCore.Qt.Key_BracketRight or k == QtCore.Qt.Key_Asterisk:
        self.RollRelDeg( 15)
        keyEvt.accept()
        return

