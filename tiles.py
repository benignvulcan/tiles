#!/usr/bin/env python

import sys, math, random
if sys.hexversion < 0x02050000:
  print "Python 2.5 minimum required."
  sys.exit(2)
from PyQt4 import QtCore, QtGui, uic

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
    if not drag_type is None:
      self._drag_type = drag_type
    if not xform_center is None:
      self._xform_center = xform_center
    else: print 'DragXformer.StartDrag: new xform_center =', xform_center
    self._start_vector = self._mouse_start - self._xform_center
  def UpdateDrag(self, mouse_pos):
    'Mouse has moved while dragging.  Update the drag transformation.'
    #print 'UpdateDrag(%s)' % (mouse_pos,)
    if self._drag_type in (DRAG_XLATE, DRAG_PAN):
      #dm = mouse_pos - self._mouse_start
      #print 'dm =', dm
      delta = mouse_pos - self._mouse_start
      self._drag_xform = QtGui.QTransform.fromTranslate(delta.x(), delta.y())
      #print '_drag_xform =', self._drag_xform
    elif self._drag_type in (DRAG_ROTATE, DRAG_ROLL):
      v2 = mouse_pos - self._xform_center
      theta = rel_angle(self._start_vector, v2)
      if self._constrain_angle:
        q = self._angular_resolution / (2*pi)
        theta = trunc(.5+theta*q) / q
      m0 = composeAffineMatrices(XlateMatrix(-self._xform_center), RotationMatrix(theta))
      self._drag_xform = composeAffineMatrices(m0, XlateMatrix(self._xform_center))
    elif self._drag_type in (DRAG_SCALE, DRAG_ZOOM):
      v2 = mouse_pos - self._xform_center
      factor = magnitude(v2) / magnitude(self._start_vector)
      m0 = composeAffineMatrices(XlateMatrix(-self._xform_center), ScaleMatrix(factor))
      self._drag_xform = composeAffineMatrices(m0, XlateMatrix(self._xform_center))
    else:
      assert not self._drag_type is None
    #assert (abs(self._drag_xform - IdentityMatrix()) > 0.00001).any()


#====

class TileItem(QtGui.QAbstractGraphicsShapeItem):
  def __init__(self, parent=None):
    QtGui.QAbstractGraphicsShapeItem.__init__(self, parent)
    self.setFlags( self.flags()
                 | QtGui.QGraphicsItem.ItemIsSelectable
                 | QtGui.QGraphicsItem.ItemIsMovable
                #| QtGui.QGraphicsItem.ItemClipsToShape
                 )
    self.setPen(QtGui.QPen(QtCore.Qt.black, 3))
    self.setBrush(QtCore.Qt.yellow)
    self.selectionPen = QtGui.QPen(QtCore.Qt.red, 3)
    self._drag_xformer = DragXformer()
  def mousePressEvent(self, event):
    if event.button() != QtCore.Qt.LeftButton:
      event.ignore()
      return
    #self.setCursor(QtCore.Qt.ClosedHandCursor)
    self.scene().clearSelection()
    self.setSelected(True)
    self._drag_xformer.StartDrag(event.pos(), DRAG_XLATE, event.pos())
    event.accept()
  def mouseMoveEvent(self, event):
    if not event.buttons():
      event.ignore()
      return
    event.accept()
    if self._drag_xformer.GetDragType() == DRAG_PAN:
      self._drag_xformer.UpdateDrag(event.pos())
    #if QtCore.QLineF(QtCore.QPointF(event.screenPos()), QtCore.QPointF(event.buttonDownScreenPos(QtCore.Qt.LeftButton))).length() < QtGui.QApplication.startDragDistance(): return
    if False:
      mimedata = QtCore.QMimeData()
      mimedata.setData(MIME_TYPE_SVG, dummySVG)
      drag = QtGui.QDrag(event.widget())
      drag.setMimeData(mimedata)
      drag.start()
      drag.exec_()
    #self.setCursor(QtCore.Qt.OpenHandCursor)
  def mouseReleaseEvent(self, event):
    self._drag_xformer.UpdateDrag(event.pos())
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
    g = RegularPolygon(sides=6, size=size)
    PolygonTileItem.__init__(self, parent, g)

#====

class TileGraphicsView(QtGui.QGraphicsView):
  def __init__(self, parent):
    QtGui.QGraphicsView.__init__(self, parent)
    self._zoom = 1.0
    self._drag_xformer = DragXformer()
    self._mouse_pos_previous = None
    self.setAcceptDrops(True)
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
  def wheelEvent(self, event):
    #print "wheelEvent.delta() =", event.delta() / 8.0
    f = self.ZOOM_FACTOR ** (event.delta() / 120.0)  # 120 = 15 degrees = 1 typical wheel step
    self.Zoom(f)
  def mousePressEvent(self, event):
    QtGui.QGraphicsView.mousePressEvent(self, event)
    if event.isAccepted():
      return
    if event.button() == QtCore.Qt.MidButton:
      self._drag_xformer.StartDrag(event.pos(), DRAG_PAN, event.pos())
      self._mouse_pos_previous = event.pos()
      assert self._mouse_pos_previous is not None
      event.accept()
  def mouseMoveEvent(self, event):
    if self._drag_xformer.GetDragType() == DRAG_PAN:
      delta = event.pos() - self._mouse_pos_previous
      hbar = self.horizontalScrollBar()
      hbar.setValue(hbar.value() - delta.x())
      vbar = self.verticalScrollBar()
      vbar.setValue(vbar.value() - delta.y())
      self._mouse_pos_previous = event.pos()
      event.accept()
      return
    QtGui.QGraphicsView.mouseMoveEvent(self, event)
  def mouseReleaseEvent(self, event):
    if self._drag_xformer.GetDragType() == DRAG_PAN:
      self._drag_xformer.UpdateDrag(event.pos())
      self._drag_xformer.ResetDrag()
      event.accept()
    else:
      QtGui.QGraphicsView.mouseReleaseEvent(self, event)
  def dragEnterEvent(self, event):
    print "TileGraphicsView.dragEnterEvent()"
    print [s for s in event.mimeData().formats()]
    if event.mimeData().hasFormat(MIME_TYPE_SVG):
      event.accept()
  #def dragMoveEvent(self, event): pass
  def dropEvent(self, event):
    print "TileGraphicsView.dropEvent()"
    event.acceptProposedAction()

#====

from mainWindow_ui import Ui_MagneticTilesMainWindow

class MagneticTilesMainWindow(Ui_MagneticTilesMainWindow, QtGui.QMainWindow):
  def __init__(self):
    QtGui.QMainWindow.__init__(self)
    Ui_MagneticTilesMainWindow.__init__(self)
    self.setupUi(self)

    self.sceneRect = QtCore.QRectF(-100, -100, 200, 200)  # orign, extent
    self.scene = QtGui.QGraphicsScene(self.sceneRect)
    self.scene.setBackgroundBrush(QtGui.QColor.fromHsv(60,2,255))
    self.scene.addItem(QtGui.QGraphicsLineItem(-100,  0, 100,0   ))
    self.scene.addItem(QtGui.QGraphicsLineItem(   0,100,   0,-100))
    self.scene.addItem(QtGui.QGraphicsRectItem(self.sceneRect))
    self.scene.addItem(QtGui.QGraphicsEllipseItem(self.sceneRect))

    for i in range(6):
      x = RegularPolygonTileItem()
      x.setBrush(QtGui.QColor.fromHsv(i*60, 255, 255))
      x.moveBy(i*10, i*10)
      self.scene.addItem(x)

    self.graphicsView.setAcceptDrops(True)
    self.graphicsView.setScene(self.scene)
    self.graphicsView.scale(4,4)
    #self.graphicsView.rotate(10)

  @QtCore.pyqtSlot()
  def on_action_Copy_triggered(self):
    #QtGui.QApplication.clipboard().setText("just a plain string", QtGui.QClipboard.Clipboard)
    mimedata = QtCore.QMimeData()
    mimedata.setData(MIME_TYPE_SVG, dummySVG)
    QtGui.QApplication.clipboard().setMimeData(mimedata)

def main():
  app = QtGui.QApplication(sys.argv)
  mainWnd = MagneticTilesMainWindow()
  mainWnd.show()
  rc = app.exec_()
  # WORKAROUND: PyQt 4.7.2 frequently segfaults if the QApplication instance
  #   is garbage collected too soon (e.g., if it is not a global variable on
  #   exiting).
  global persistent_app
  persistent_app = app


if __name__=='__main__': main()
