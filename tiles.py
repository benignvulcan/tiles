#!/usr/bin/env python3

import sys, math, random
import xml.etree.ElementTree as ET
if sys.hexversion < 0x03040000:
  print("Python 3.4 minimum required.")
  sys.exit(2)
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from qmathturtle import RecordingTurtle

_debug = True

MIME_TYPE_SVG = "image/svg+xml"

XML_decl = '<?xml version="1.0" encoding="utf-8" standalone="no"?>'
DOCTYPE_decl = '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">'
SVG_sample = \
'''<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="100" height="100">
  <rect x="0" y="0" width="1" height="1" stroke="#00F" stroke-width=".01" fill="none" />
  <circle cx="0" cy="0" r="1" stroke="black" stroke-width=".01" fill="#FCF" fill-opacity="0.75" />
  <polygon points=".850,.075 .958,.1375 .958,.2625 .850,.325 .742,.2626 .742,.1375" stroke="purple" stroke-width=".03" fill="yellow" />
</svg>
'''
dummySVG = XML_decl + DOCTYPE_decl + SVG_sample

def RegularPolygon(sides=6, size=None, r=None, rotate=0.0):
  # Must provide one of size or r, size overrides r
  theta = 2*math.pi/sides
  if r is None:
    r = math.sqrt(size*size/(2*(1-math.cos(theta))))
  rotate = rotate + theta/2
  return QtGui.QPolygonF(map(lambda i: QtCore.QPointF(r*math.cos(i*theta+rotate), r*math.sin(i*theta+rotate))
                            ,range(sides)
                            )
                        )

def FormatQTransform(xform):
  "Return a string representing the QTransform's matrix"
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
  '''A QGraphicsItem that can be moved/rotated/scaled by the user
     and can snap to other TileItems'''
  def __init__(self, parent=None):
    QtWidgets.QAbstractGraphicsShapeItem.__init__(self, parent)
    self.setFlags( self.flags()
                 | QtWidgets.QGraphicsItem.ItemIsSelectable
                 | QtWidgets.QGraphicsItem.ItemIsMovable
                #| QtWidgets.QGraphicsItem.ItemClipsToShape
                 )
    self.setPen(QtGui.QPen(QtCore.Qt.black, .01))
    self.setBrush(QtCore.Qt.yellow)
    self.selectionPen = QtGui.QPen(QtCore.Qt.red, .05)
    self._drag_type = DRAG_NONE
    #self._drag_xformer = DragXformer()
  def center(self):
    return self.boundingRect().center()
  def sceneCenter(self):
    return self.sceneTransform().map(self.center())
  def snapPolygon(self):
    return QtGui.QPolygonF()
  def snapVertices(self):
    return [p for p in self.snapPolygon()]
  def nearestSnaps(self, snap_dist, exclude=None):
    "Return a list of (equally) closest snap-tuples."
    snap_margins = QtCore.QMarginsF(snap_dist,snap_dist,snap_dist,snap_dist)
    snap_search_rect = self.mapToScene(self.boundingRect().marginsAdded(snap_margins))
    nearby_items = self.scene().items(snap_search_rect)
    nearby_tiles = [it for it in nearby_items if hasattr(it, "snapPolygon") and not it is self]
    self_scenePoly = self.mapToScene(self.snapPolygon())
    nearest_dist2 = snap_dist * snap_dist  # Use squared distances to avoid calling sqrt
    nearest = []  # list of nearby pairs of points
    for other_tile in nearby_tiles:
      other_scenePoly = other_tile.mapToScene(other_tile.snapPolygon())
      for p in self_scenePoly:
        for q in other_scenePoly:
          pq = p - q
          pq2 = pq.x()**2 + pq.y()**2
          if pq2 <= nearest_dist2:
            if pq2 < nearest_dist2:
              nearest_dist2 = pq2
              nearest = [n for n in nearest if n[0] <= nearest_dist2]
            nearest.append( (pq2, p,q, other_tile) )
    return nearest
  def mousePressEvent(self, gsMouseEvt):
    #print("TileItem.mousePressEvent(): scenePos={}".format(gsMouseEvt.scenePos()))
    self.scene().clearSelection()
    #self.setCursor(QtCore.Qt.ClosedHandCursor)
    self.setSelected(True)
    if gsMouseEvt.button() == QtCore.Qt.LeftButton:
      self._drag_type = DRAG_XLATE
      #return super().mousePressEvent(gsMouseEvt)
    elif gsMouseEvt.button() == QtCore.Qt.RightButton:
      self._drag_type = DRAG_ROTATE
    elif gsMouseEvt.button() == QtCore.Qt.MiddleButton:
      self._drag_type = DRAG_SCALE
    else:
      gsMouseEvt.ignore()
      if _debug: print("TileItem.mousePressEvent() ignoring non LeftButton")
      return
    self._drag_start_xform = self.transform()
    self._drag_start_pos = gsMouseEvt.scenePos()
    xformCenter = self.mapToScene(QtCore.QPointF(0,0))
    self._drag_start_vector = QtCore.QLineF(xformCenter, self._drag_start_pos)
    #self._drag_xformer.StartDrag(gsMouseEvt.scenePos(), self._drag_type, gsMouseEvt.scenePos())
    #self.resetTransform()
    #self.setTransform( self._drag_xformer.Transform() )
    gsMouseEvt.accept()
  def mouseMoveEvent(self, gsMouseEvt):
    #print("TileItem.mouseMoveEvent(): scenePos={}".format(gsMouseEvt.scenePos()))
    if not gsMouseEvt.buttons():
      gsMouseEvt.ignore()
      if _debug: print("TileItem.mouseMoveEvent() ignoring NO BUTTONS")
      return
    #if self._drag_xformer.GetDragType() == DRAG_XLATE:
    #if QtCore.QLineF(QtCore.QPointF(gsMouseEvt.screenPos()), QtCore.QPointF(gsMouseEvt.buttonDownScreenPos(QtCore.Qt.LeftButton))).length() < QtWidgets.QApplication.startDragDistance(): return
    if self._drag_type == DRAG_XLATE:
      #return super().mouseMoveEvent(gsMouseEvt)
      offset_from_start = self.mapFromScene(gsMouseEvt.scenePos()) - self.mapFromScene(self._drag_start_pos)
      #self.setPos(offset_from_start)
      xform = QtGui.QTransform(self._drag_start_xform).translate(offset_from_start.x(),offset_from_start.y())
    elif self._drag_type == DRAG_ROTATE:
      move_vector = QtCore.QLineF(self._drag_start_vector.p1(), gsMouseEvt.scenePos())
      theta = move_vector.angleTo(self._drag_start_vector)
      if True:
        angular_resolution = 180
        q = 360.0 / angular_resolution
        theta = q * round(float(theta) / q)
      xform = QtGui.QTransform(self._drag_start_xform).rotate(theta)
    elif self._drag_type == DRAG_SCALE:
      move_vector = QtCore.QLineF(self._drag_start_vector.p1(), gsMouseEvt.scenePos())
      scaleFactor = move_vector.length() / self._drag_start_vector.length()
      if True:
        # TODO: round to integral multiples/fractions of: 1, sqrt(2), phi, sqrt(3), e, pi
        if scaleFactor >= 1:
          scaleFactor = round(scaleFactor)
        else:
          scaleFactor = 1 /  round(1/scaleFactor)
      xform = QtGui.QTransform(self._drag_start_xform).scale(scaleFactor, scaleFactor)
    else:
      #self._drag_xformer.UpdateDrag(gsMouseEvt.scenePos())
      #self.setTransform( self._drag_xformer.Transform() )
      return
    self.setTransform(xform)
    if self.scene().snapEnabled: #property("snapEnabled"):
      nearSnaps = self.nearestSnaps(self.scene().snapDist)
      if nearSnaps:
        if _debug: print("snapDist {}: {} snaps".format(self.scene().snapDist, len(nearSnaps)))
        nearSnaps.sort()
        pq2, p, q, otherTile = nearSnaps[0]  # pick an arbitrary snap
        snapDelta = self.mapFromScene(q) - self.mapFromScene(p)
        xform.translate(snapDelta.x(), snapDelta.y())
        self.setTransform(xform)
    if False:
      mimedata = QtCore.QMimeData()
      mimedata.setData(MIME_TYPE_SVG, dummySVG)
      drag = QtGui.QDrag(gsMouseEvt.widget())
      drag.setMimeData(mimedata)
      drag.exec_()
    #self.setCursor(QtCore.Qt.OpenHandCursor)
    gsMouseEvt.accept()
  def mouseReleaseEvent(self, gsMouseEvt):
    #print("TileItem.mouseReleaseEvent(): scenePos={}".format(gsMouseEvt.scenePos()))
    xforms = self.transformations()
    if xforms and _debug: print("{} transformations set!".format(len(xforms)))
    if self._drag_type == DRAG_XLATE:
      self._drag_type = DRAG_NONE
      return super().mouseReleaseEvent(gsMouseEvt)
    elif self._drag_type == DRAG_ROTATE or self._drag_type == DRAG_SCALE:
      self._drag_type = DRAG_NONE
      gsMouseEvt.accept()
      return
    #self._drag_xformer.UpdateDrag(gsMouseEvt.scenePos())
    #self.setTransform( self._drag_xformer.Transform() )
    #self._drag_xformer.ResetDrag()
    #self.setCursor(QtCore.Qt.OpenHandCursor)

class PolygonTileItem(TileItem):
  def __init__(self, parent=None, polygon=None):
    TileItem.__init__(self, parent)
    self._polygon = polygon
  def shape(self):
    "Return shape for collision/hit testing"
    path = QtGui.QPainterPath()
    path.addPolygon(self._polygon)
    path.closeSubpath()
    return path
  def snapPolygon(self):
    return QtGui.QPolygonF(self._polygon)
  def boundingRect(self):
    return self._polygon.boundingRect()
  def paint(self, painter, option, widget=0):
    painter.setPen(self.pen())
    path = QtGui.QPainterPath()
    if _debug:
      painter.drawRect(self.boundingRect())  # debug bounding rect
    else:
      # Prevent paint from falling outside the lines
      path.addPolygon(self._polygon)
      path.closeSubpath()
      painter.setClipPath(path)
    painter.setBrush(self.brush())
    painter.drawPolygon(self._polygon)
    if self.isSelected():
      painter.setPen(self.selectionPen)
      painter.drawPolygon(self._polygon)
    if _debug:
      painter.setBrush(QtCore.Qt.NoBrush)
      painter.setPen(QtGui.QPen(QtCore.Qt.green, .03))
      painter.drawEllipse(self._polygon[0], .05, .05)  # indicate first vertex
      painter.setPen(QtGui.QPen(QtCore.Qt.blue, .03))
      painter.drawEllipse(QtCore.QPointF(0,0), .05, .05)     # indicate center of rotation
  def as_pixmap(self):
    pass
  def toSvg(self, parent):
    attrs = \
      { 'points' : ' '.join('{},{}'.format(p.x(),p.y()) for p in self._polygon)
      , 'stroke' : self.pen().color().name()
      , 'stroke-width': '.03'
      , 'fill' : self.brush().color().name()
      }
    ET.SubElement(parent, 'polygon', attrib=attrs)

class RegularPolygonTileItem(PolygonTileItem):
  def __init__(self, parent=None, sides=6, size=1):
    g = RegularPolygon(sides=sides, size=size)
    PolygonTileItem.__init__(self, parent, g)

def Arrowhead(size=1):
  "Return a concave symmetrical quadrilateral"
  # TODO: calibrate to unit scale & nice angles
  # (concavity should be right angle, points should snap to square grid?)
  #t = QMathTurtle().rt(math.radians(180+72)).fd(1).rt(math.radians(18+180-36)).fd(.5).lt(math.radians(72)).fd(.5)
  t = RecordingTurtle().lt(180+72).fd(1).rt(72+72).fd(1).rt(18+90+45).fd(.5)
  poly = t.polygon()
  poly.translate(QtCore.QPointF(0,0)-poly.boundingRect().center())
  return PolygonTileItem(polygon=poly)
  return PolygonTileItem(polygon=QtGui.QPolygonF(map(lambda p: QtCore.QPointF(*p),
    [(0,.25*size),(.75*size,size),(0,-size),(-.75*size,size),(0,.25*size)])))

#====

class TileGraphicsView(QtWidgets.QGraphicsView):
  def __init__(self, parent):
    super().__init__(parent)
    self._zoom = 1.0
    self.setAcceptDrops(True)
    self._angular_resolution = 120  # foldl1 lcm [3,4,5,6,8]
    #self.dragMode = QtWidgets.QGraphicsView.ScrollHandDrag  # what to do wtih mouse clicks not caught by a GraphicsItem
    self._drag_type = DRAG_NONE
    self._drag_start_pos = None
    self._drag_last_pos = None
  ZOOM_FACTOR=math.sqrt(2)
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
    super().mousePressEvent(mouseEvt)
    if mouseEvt.isAccepted():
      # Parent mousePressEvent found a GraphicsItem to handle this mouseEvt.
      return
    # User is trying to mouse on background.
    if mouseEvt.button() == QtCore.Qt.MidButton:
      # Middle button pans scene
      self._drag_type = DRAG_PAN
      self._drag_last_pos = mouseEvt.pos()
      assert self._drag_last_pos is not None
      mouseEvt.accept()
    elif mouseEvt.button() == QtCore.Qt.RightButton:
      self._drag_type = DRAG_ROLL
      self._drag_start_xform = self.transform()
      self._drag_start_pos = mouseEvt.pos()
      self._drag_start_vector = QtCore.QLineF(self.rect().center(), self._drag_start_pos)
      mouseEvt.accept()
    # otherwise ignore
  def mouseMoveEvent(self, mouseEvt):
    if self._drag_type == DRAG_PAN:
      delta = mouseEvt.pos() - self._drag_last_pos
      hbar = self.horizontalScrollBar()
      hbar.setValue(hbar.value() - delta.x())
      vbar = self.verticalScrollBar()
      vbar.setValue(vbar.value() - delta.y())
      self._drag_last_pos = mouseEvt.pos()
      mouseEvt.accept()
      return
    elif self._drag_type == DRAG_ROLL:
      move_vector = QtCore.QLineF(self.rect().center(), mouseEvt.pos())
      theta = move_vector.angleTo(self._drag_start_vector)
      if True:
        q = 360.0 / self._angular_resolution
        theta = q * round(float(theta) / q)
      self.setTransform(QtGui.QTransform(self._drag_start_xform).rotate(theta))
      mouseEvt.accept()
    else:
      super().mouseMoveEvent(mouseEvt)
  def mouseReleaseEvent(self, mouseEvt):
    if self._drag_type != DRAG_NONE:
      self._drag_type = DRAG_NONE
      mouseEvt.accept()
    else:
      super().mouseReleaseEvent(mouseEvt)
  def dragEnterEvent(self, dragEnterEvt):
    if _debug: print("TileGraphicsView.dragEnterEvent()")
    if _debug: print([s for s in dragEnterEvt.mimeData().formats()])
    if dragEnterEvt.mimeData().hasFormat(MIME_TYPE_SVG):
      dragEnterEvt.accept()
  #def dragMoveEvent(self, dragMoveEvt): pass
  def dropEvent(self, dropEvt):
    if _debug: print("TileGraphicsView.dropEvent()")
    dropEvt.acceptProposedAction()

#====

from mainWindow_ui import Ui_MagneticTilesMainWindow

class MagneticTilesMainWindow(Ui_MagneticTilesMainWindow, QtWidgets.QMainWindow):
  '''A MainWindow supporting use of a TileGraphicsView onto a QGraphicsScene
      containing magnetic TileItems to interact with.'''
  # Note that the GUI attributes of this class/window are defined in
  # mainWindow.ui (compiled by pyuic to mainWindow_ui.py), edited using Qt Creator:
  #   centralWidget = QWidget()
  #   graphicsView = TileGraphicsView()
  #   menubar
  #   statusbar
  def __init__(self):
    QtWidgets.QMainWindow.__init__(self)
    Ui_MagneticTilesMainWindow.__init__(self)
    self.setupUi(self)

    # Create scene
    self.sceneRect = QtCore.QRectF( -10, -10   # origin
                                  ,  20,  20)  # extent
    self.scene = QtWidgets.QGraphicsScene(self.sceneRect)
    self.scene.snapEnabled = True
    #bSetExisting = self.scene.setProperty("snapEnabled", True)
    #print("bSetExisting = ", bSetExisting)
    self.scene.snapDist = .1
    self.scene.setBackgroundBrush(QtGui.QColor.fromHsv(60,15,255))

    titleItem = QtWidgets.QGraphicsSimpleTextItem("Magnetic Tiles")
    titleItem.setScale(.1)
    titleItem.moveBy(-5,-9)
    self.scene.addItem(titleItem)

    # Add (non-tile, background) lines
    hLines = [ QtWidgets.QGraphicsLineItem(-10,y,10,y) for y in range(-10,10) ]
    vLines = [ QtWidgets.QGraphicsLineItem(x,-10,x,10) for x in range(-10,10) ]
    lineItems = \
      [ QtWidgets.QGraphicsLineItem(-10,  0, 10,0   )  # x axis
      , QtWidgets.QGraphicsLineItem(   0,10,   0,-10)  # y axis
      , QtWidgets.QGraphicsRectItem(self.sceneRect)    # scene boundary
      , QtWidgets.QGraphicsEllipseItem(self.sceneRect) # "calibration" circle
      , QtWidgets.QGraphicsRectItem(-.5,-.5,1,1)       # unit square
      , QtWidgets.QGraphicsEllipseItem(-.5,-.5,1,1)    # unit circle
      ]
    linePen = QtGui.QPen(QtCore.Qt.black, .01)
    for it in hLines + vLines + lineItems:
      it.setPen(linePen)
      self.scene.addItem(it)

    # Create some initial tiles
    m = 12
    for i in range(26):
      x = RegularPolygonTileItem()  # Add default hexagon
      hue = i*(360/m)%360
      x.setBrush(QtGui.QColor.fromHsv(hue, 255, 255))
      #x.setRotation(random.randrange(12)*30)
      x.setTransform(QtGui.QTransform().rotate(random.randrange(12)*30))
      #x.moveBy(i-2, i-2)
      x.moveBy(random.randrange(-9,9), random.randrange(-9,9))
      x.setOpacity(.75)
      self.scene.addItem(x)
      label = QtWidgets.QGraphicsSimpleTextItem(chr(ord('A')+i))
      label.setParentItem(x)
      label.setScale(.1)
      #label.moveBy(-.5,-.75)
      rect = label.mapRectToParent(label.boundingRect())
      label.setPos(-rect.width()/2, -rect.height()/2)
    arrowhead = Arrowhead(1)
    arrowhead.setBrush(QtGui.QColor.fromHsv(50,255,255))
    arrowhead.moveBy(-3,-3)
    self.scene.addItem(arrowhead)

    # Get ready to go
    self.graphicsView.setAcceptDrops(True)
    self.graphicsView.setScene(self.scene)
    # Default view scaling is 1 = 1 px
    self.graphicsView.scale(20,20)  # set to 1 = 4 px
    #self.graphicsView.rotate(10)

  @QtCore.pyqtSlot()
  def on_action_Copy_triggered(self):
    if _debug: print("Copy_triggered")
    #QtWidgets.QApplication.clipboard().setText("just a plain string", QtGui.QClipboard.Clipboard)
    mimedata = QtCore.QMimeData()
    mimedata.setData(MIME_TYPE_SVG, dummySVG)
    QtWidgets.QApplication.clipboard().setMimeData(mimedata)

  @QtCore.pyqtSlot()
  def on_action_Delete_triggered(self):
    if _debug: print("Delete_triggered")

  @QtCore.pyqtSlot()
  def on_action_Cut_triggered(self):
    if _debug: print("Cut_triggered")

  @QtCore.pyqtSlot()
  def on_action_Paste_triggered(self):
    if _debug: print("Paste_triggered")

  @QtCore.pyqtSlot()
  def on_action_Save_triggered(self):
    if _debug: print("Save_triggered")
    ET.register_namespace('','http://www.w3.org/2000/svg')
    doc = ET.Element('svg', xmlns='http://www.w3.org/2000/svg', version='1.1', width='10', height='10')
    f = open('output.svg', 'wt')
    if f:
      for it in self.scene.items(order=QtCore.Qt.AscendingOrder):
        if hasattr(it, 'toSvg'):
          it.toSvg(doc)
      contents = '\n'.join([XML_decl, DOCTYPE_decl, ET.tostring(doc, encoding='unicode')])
      if _debug: print(contents)
      f.write(contents)
      f.close()
      if _debug: print('saved')

  @QtCore.pyqtSlot()
  def on_action_Open_triggered(self):
    if _debug: print("Open_triggered")

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
