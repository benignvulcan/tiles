#!/usr/bin/env python3

import sys, math, random
if sys.hexversion < 0x03040000:
  print("Python 3.4 minimum required.")
  sys.exit(2)
from PyQt5 import QtCore, QtGui, QtWidgets, uic

MIME_TYPE_SVG = "image/svg+xml"

dummySVG = '''<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg height="360" version="1.1" width="480" xmlns="http://www.w3.org/2000/svg">
<rect fill="none" height="100%" stroke="#00F" width="100%" />
<circle cx="240" cy="180" fill="#FCF" r="160" stroke="black" />
</svg>
'''

def RegularPolygon(sides=6, size=None, r=None, rotate=0.0):
  # size overrides r
  theta = 2*math.pi/sides
  if r is None:
    r = math.sqrt(size*size/(2*(1-math.cos(theta))))
  rotate = rotate + theta/2
  return QtGui.QPolygonF(map(lambda i: QtCore.QPointF(r*math.cos(i*theta+rotate), r*math.sin(i*theta+rotate))
                            ,range(sides)
                            )
                        )

def FormatQTransform(xform):
  fmtDict = {}
  fmtFields = []
  for row in (1,2,3):
    for col in (1,2,3):
      attr = "m{}{}".format(row,col)
      fmtDict[attr] = getattr(xform, attr)()
      fmtFields.append("{"+attr+"}")
  return "[{}]".format(','.join(fmtFields).format(**fmtDict))

#====

# constants for different dragging states
DRAG = '*DRAG*'
DRAG_NONE   = (0, DRAG)
DRAG_XLATE  = (1, DRAG)
DRAG_ROTATE = (2, DRAG)
DRAG_SCALE  = (3, DRAG)
DRAG_PAN    = (4, DRAG)
DRAG_ROLL   = (5, DRAG)
DRAG_ZOOM   = (6, DRAG) # or DOLLY
#DRAG_SELECTBOX = (7, DRAG) # or MARQUEE? or RUBBERBAND?

class DragXformer(object):
  'Given information about mouse drags, maintain a transformation matrix.'
  def __init__(self, xform_center=None):
    object.__init__(self)
    self._xform_center = xform_center   # Center of transformation
    self._angular_resolution = 120 #360  # round to nearest fraction of circle
    self._constrain_angle = True
    self.ResetDrag()
  def ResetDrag(self):
    self._drag_xform = QtGui.QTransform()
    self._drag_type = DRAG_NONE         # XLATE/ROTATE/SCALE
    self._mouse_start = None            # starting position of mouse
    #assert (self._drag_xform == IdentityMatrix()).all()
  def GetDragType(self):
    return self._drag_type
  def Transform(self):
    return self._drag_xform
  def StartDrag(self, mouse_pos=None, drag_type=None, xform_center=None):
    'Some kind of dragging has started.  Remember the starting position of mouse.'
    self._mouse_start = mouse_pos
    print('DragXformer.StartDrag(mouse_pos={}, drag_type={}, xform_center={})'.format(mouse_pos,drag_type,xform_center))
    if not drag_type is None:
      self._drag_type = drag_type
    if not xform_center is None:
      self._xform_center = xform_center
    else: print('DragXformer.StartDrag: new xform_center =', xform_center)
    #self._start_vector = self._mouse_start - self._xform_center
    self._start_vector = QtCore.QLineF(self._xform_center, self._mouse_start)
  def UpdateDrag(self, mouse_pos):
    'Mouse has moved while dragging.  Update the drag transformation.'
    print('DragXformer.UpdateDrag({})'.format(mouse_pos))
    if self._drag_type in (DRAG_XLATE, DRAG_PAN):
      #dm = mouse_pos - self._mouse_start
      #print 'dm =', dm
      delta = mouse_pos - self._mouse_start
      self._drag_xform = QtGui.QTransform.fromTranslate(delta.x(), delta.y())
      print('DragXformer._drag_xform = {}'.format(FormatQTransform(self._drag_xform)))
    elif self._drag_type in (DRAG_ROTATE, DRAG_ROLL):
      #v2 = mouse_pos - self._xform_center
      v2 = QtCore.QLineF(self._xform_center, mouse_pos)
      #theta = rel_angle(self._start_vector, v2)
      theta = self._start_vector.angleTo(v2)
      print(v2, theta)
      if self._constrain_angle:
        q = self._angular_resolution / 360 #(2*math.pi)
        #theta = math.trunc(.5+theta*q) / q
        theta = self._angular_resolution * round(float(theta) / self._angular_resolution)
      # TODO: find Qt equivalent of affine matrix composition
      #m0 = composeAffineMatrices(XlateMatrix(-self._xform_center), RotationMatrix(theta))
      #self._drag_xform = composeAffineMatrices(m0, XlateMatrix(self._xform_center))
      self._drag_xform.rotate(theta)
    elif self._drag_type in (DRAG_SCALE, DRAG_ZOOM):
      v2 = mouse_pos - self._xform_center
      factor = magnitude(v2) / magnitude(self._start_vector)
      m0 = composeAffineMatrices(XlateMatrix(-self._xform_center), ScaleMatrix(factor))
      self._drag_xform = composeAffineMatrices(m0, XlateMatrix(self._xform_center))
    else:
      assert not self._drag_type is None
    #assert (abs(self._drag_xform - IdentityMatrix()) > 0.00001).any()


#====

class TileItem(QtWidgets.QAbstractGraphicsShapeItem):
  def __init__(self, parent=None):
    QtWidgets.QAbstractGraphicsShapeItem.__init__(self, parent)
    self.setFlags( self.flags()
                 | QtWidgets.QGraphicsItem.ItemIsSelectable
                 | QtWidgets.QGraphicsItem.ItemIsMovable
                #| QtWidgets.QGraphicsItem.ItemClipsToShape
                 )
    self.setPen(QtGui.QPen(QtCore.Qt.black, 3))
    self.setBrush(QtCore.Qt.yellow)
    self.selectionPen = QtGui.QPen(QtCore.Qt.red, 3)
    self._drag_type = None
    self._drag_xformer = DragXformer()
  def center(self):
    return self.boundingRect().center()
  def sceneCenter(self):
    return self.sceneTransform().map(self.center())
  def mousePressEvent(self, gsMouseEvt):
    print("TileItem.mousePressEvent(): scenePos={}".format(gsMouseEvt.scenePos()))
    if gsMouseEvt.button() == QtCore.Qt.LeftButton:
      self._drag_type = DRAG_XLATE
      return super().mousePressEvent(gsMouseEvt)
    self.scene().clearSelection()
    #self.setCursor(QtCore.Qt.ClosedHandCursor)
    self.setSelected(True)
    if gsMouseEvt.button() == QtCore.Qt.LeftButton:
      self._drag_type = DRAG_XLATE
      self._drag_start_pos = gsMouseEvt.scenePos()
    elif gsMouseEvt.button() == QtCore.Qt.RightButton:
      self._drag_type = DRAG_ROTATE
      self._drag_start_xform = self.transform()
      self._drag_start_pos = gsMouseEvt.scenePos()
      self._drag_start_vector = QtCore.QLineF(self.sceneCenter(), self._drag_start_pos)
    elif gsMouseEvt.button() == QtCore.Qt.MiddleButton:
      self._drag_type = DRAG_SCALE
    else:
      gsMouseEvt.ignore()
      print("TileItem.mousePressEvent() ignoring non LeftButton")
      return
    self._drag_xformer.StartDrag(gsMouseEvt.scenePos(), self._drag_type, gsMouseEvt.scenePos())
    #self.resetTransform()
    #self.setTransform( self._drag_xformer.Transform() )
    gsMouseEvt.accept()
  def mouseMoveEvent(self, gsMouseEvt):
    print("TileItem.mouseMoveEvent(): scenePos={}".format(gsMouseEvt.scenePos()))
    if self._drag_type == DRAG_XLATE:
      return super().mouseMoveEvent(gsMouseEvt)
    if not gsMouseEvt.buttons():
      gsMouseEvt.ignore()
      print("TileItem.mouseMoveEvent() ignoring NO BUTTONS")
      return
    #if self._drag_xformer.GetDragType() == DRAG_XLATE:
    #if QtCore.QLineF(QtCore.QPointF(gsMouseEvt.screenPos()), QtCore.QPointF(gsMouseEvt.buttonDownScreenPos(QtCore.Qt.LeftButton))).length() < QtWidgets.QApplication.startDragDistance(): return
    if self._drag_type == DRAG_XLATE:
      self.setPos(gsMouseEvt.scenePos() - self._drag_start_pos)
      gsMouseEvt.accept()
      return
    if self._drag_type == DRAG_ROTATE:
      move_vector = QtCore.QLineF(self.sceneCenter(), gsMouseEvt.scenePos())
      theta = move_vector.angleTo(self._drag_start_vector)
      self.setTransform(QtGui.QTransform(self._drag_start_xform).rotate(theta))
      gsMouseEvt.accept()
      return
    self._drag_xformer.UpdateDrag(gsMouseEvt.scenePos())
    self.setTransform( self._drag_xformer.Transform() )
    if False:
      mimedata = QtCore.QMimeData()
      mimedata.setData(MIME_TYPE_SVG, dummySVG)
      drag = QtGui.QDrag(gsMouseEvt.widget())
      drag.setMimeData(mimedata)
      drag.start()
      drag.exec_()
    #self.setCursor(QtCore.Qt.OpenHandCursor)
    gsMouseEvt.accept()
  def mouseReleaseEvent(self, gsMouseEvt):
    print("TileItem.mouseReleaseEvent(): scenePos={}".format(gsMouseEvt.scenePos()))
    if self._drag_type == DRAG_XLATE:
      self._drag_type = None
      return super().mouseReleaseEvent(gsMouseEvt)
    elif self._drag_type == DRAG_ROTATE:
      self._drag_type = None
      gsMouseEvt.accept()
      return
    self._drag_xformer.UpdateDrag(gsMouseEvt.scenePos())
    self.setTransform( self._drag_xformer.Transform() )
    self._drag_xformer.ResetDrag()
    #self.setCursor(QtCore.Qt.OpenHandCursor)

class PolygonTileItem(TileItem):
  def __init__(self, parent=None, polygon=None):
    TileItem.__init__(self, parent)
    self.polygon = polygon
  def boundingRect(self):
    return self.polygon.boundingRect()
  def paint(self, painter, option, widget=0):
    path = QtGui.QPainterPath()
    path.addPolygon(self.polygon)
    path.closeSubpath()
    painter.setClipPath(path)

    painter.setPen(self.pen())
    painter.setBrush(self.brush())
    painter.drawPolygon(self.polygon)

    if self.isSelected():
      painter.setPen(self.selectionPen)
      painter.drawPolygon(self.polygon)
  def as_pixmap(self):
    pass

class RegularPolygonTileItem(PolygonTileItem):
  def __init__(self, parent=None, sides=6, size=8):
    g = RegularPolygon(sides=sides, size=size)
    PolygonTileItem.__init__(self, parent, g)

def Arrowhead(size=8):
  "Return a concave symmetrical quadrilateral"
  # TODO: calibrate to unit scale & nice angles
  # (concavity should be right angle, points should snap to square grid?)
  return PolygonTileItem(polygon=QtGui.QPolygonF(map(lambda p: QtCore.QPointF(*p),
    [(0,.25*size),(.75*size,size),(0,-size),(-.75*size,size),(0,.25*size)])))

#====

class TileGraphicsView(QtWidgets.QGraphicsView):
  def __init__(self, parent):
    QtWidgets.QGraphicsView.__init__(self, parent)
    self._zoom = 1.0
    self._drag_xformer = DragXformer()
    self._mouse_pos_previous = None
    self.setAcceptDrops(True)
    #self.dragMode = QtWidgets.QGraphicsView.ScrollHandDrag  # what to do wtih mouse clicks not caught by a GraphicsItem
  ZOOM_FACTOR=1.5
  def Zoom(self, f=None):
    if f is None: f = self.ZOOM_FACTOR
    z = self._zoom * f
    if z > .001 and z < 1000:
      self._zoom = z
      self.scale(f,f)
  def ZoomIn(self):
    self.Zoom(self.ZOOM_FACTOR)
  def ZoomOut(self):
    self.Zoom(1/self.ZOOM_FACTOR)
  def wheelEvent(self, mouseEvt):
    #print "wheelEvent.delta() =", mouseEvt.delta() / 8.0
    f = self.ZOOM_FACTOR ** (mouseEvt.angleDelta().y() / 120.0)  # 120 = 15 degrees = 1 typical wheel step
    self.Zoom(f)
  def mousePressEvent(self, mouseEvt):
    # Use overridden parent to do standard event multiplexing to scene items:
    QtWidgets.QGraphicsView.mousePressEvent(self, mouseEvt)
    if mouseEvt.isAccepted():
      # Parent mousePressEvent found a GraphicsItem to handle this mouseEvt.
      return
    # User is trying to mouse on background.
    if mouseEvt.button() == QtCore.Qt.MidButton:
      # Middle button pans scene
      self._drag_xformer.StartDrag(mouseEvt.pos(), DRAG_PAN, mouseEvt.pos())
      self._mouse_pos_previous = mouseEvt.pos()
      assert self._mouse_pos_previous is not None
      mouseEvt.accept()
    # otherwise ignore
  def mouseMoveEvent(self, mouseEvt):
    if self._drag_xformer.GetDragType() == DRAG_PAN:
      self._drag_xformer.UpdateDrag(mouseEvt.pos())  # DRAG XFORMER NOT ACTUALLY USED YET
      delta = mouseEvt.pos() - self._mouse_pos_previous
      hbar = self.horizontalScrollBar()
      hbar.setValue(hbar.value() - delta.x())
      vbar = self.verticalScrollBar()
      vbar.setValue(vbar.value() - delta.y())
      self._mouse_pos_previous = mouseEvt.pos()
      mouseEvt.accept()
      return
    QtWidgets.QGraphicsView.mouseMoveEvent(self, mouseEvt)
  def mouseReleaseEvent(self, mouseEvt):
    if self._drag_xformer.GetDragType() == DRAG_PAN:
      self._drag_xformer.UpdateDrag(mouseEvt.pos())
      self._drag_xformer.ResetDrag()
      mouseEvt.accept()
    else:
      QtWidgets.QGraphicsView.mouseReleaseEvent(self, mouseEvt)
  def dragEnterEvent(self, dragEnterEvt):
    print("TileGraphicsView.dragEnterEvent()")
    print([s for s in dragEnterEvt.mimeData().formats()])
    if dragEnterEvt.mimeData().hasFormat(MIME_TYPE_SVG):
      dragEnterEvt.accept()
  #def dragMoveEvent(self, dragMoveEvt): pass
  def dropEvent(self, dropEvt):
    print("TileGraphicsView.dropEvent()")
    dropEvt.acceptProposedAction()

#====

from mainWindow_ui import Ui_MagneticTilesMainWindow

class MagneticTilesMainWindow(Ui_MagneticTilesMainWindow, QtWidgets.QMainWindow):
  def __init__(self):
    QtWidgets.QMainWindow.__init__(self)
    Ui_MagneticTilesMainWindow.__init__(self)
    self.setupUi(self)

    self.sceneRect = QtCore.QRectF(-100, -100, 200, 200)  # orign, extent
    self.scene = QtWidgets.QGraphicsScene(self.sceneRect)
    self.scene.setBackgroundBrush(QtGui.QColor.fromHsv(60,2,255))
    self.scene.addItem(QtWidgets.QGraphicsLineItem(-100,  0, 100,0   ))
    self.scene.addItem(QtWidgets.QGraphicsLineItem(   0,100,   0,-100))
    self.scene.addItem(QtWidgets.QGraphicsRectItem(self.sceneRect))
    self.scene.addItem(QtWidgets.QGraphicsEllipseItem(self.sceneRect))

    for i in range(6):
      x = RegularPolygonTileItem()
      x.setBrush(QtGui.QColor.fromHsv(i*60, 255, 255))
      x.moveBy(i*10, i*10)
      self.scene.addItem(x)
    arrowhead = Arrowhead(12)
    arrowhead.setBrush(QtGui.QColor.fromHsv(50,255,255))
    arrowhead.moveBy(-20,-20)
    self.scene.addItem(arrowhead)

    self.graphicsView.setAcceptDrops(True)
    self.graphicsView.setScene(self.scene)
    self.graphicsView.scale(4,4)
    #self.graphicsView.rotate(10)

  @QtCore.pyqtSlot()
  def on_action_Copy_triggered(self):
    #QtWidgets.QApplication.clipboard().setText("just a plain string", QtGui.QClipboard.Clipboard)
    mimedata = QtCore.QMimeData()
    mimedata.setData(MIME_TYPE_SVG, dummySVG)
    QtWidgets.QApplication.clipboard().setMimeData(mimedata)

def main():
  app = QtWidgets.QApplication(sys.argv)
  mainWnd = MagneticTilesMainWindow()
  mainWnd.show()
  rc = app.exec_()
  # WORKAROUND: PyQt 4.7.2 frequently segfaults if the QApplication instance
  #   is garbage collected too soon (e.g., if it is not a global variable on
  #   exiting).
  global persistent_app
  persistent_app = app


if __name__=='__main__': main()
