#!/usr/bin/env python3

import math, random, re
from math import pi, degrees, radians, sqrt, sin, cos, tan, atan2, asin, acos
#from abc import ABCMeta, abstractmethod, abstractclassmethod

import xml.etree.ElementTree as ET

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QPointF, QLineF
from PyQt5.QtGui import QPolygonF

import svgparsing
from qmathturtle import RecordingTurtle
from q2str import *

logger = None

#==== QPolygonF creating functions

PHI = (1+sqrt(5))/2

def QPolygonFArea(p):
  # Self-intersecting polygons will include regions of multiplied or negative area.
  n = len(p)
  a = 0
  for i in range(n):
    j = (i+1)%n
    a += p[i].x()*p[j].y() - p[j].x()*p[i].y()
  return a/2.0

_xformFlipY = QtGui.QTransform.fromScale(1,-1)

def YFlippedPolygonF(p):
  return _xformFlipY.map(p)

def RecenteredPolygonF(p):
  return p.translated(QtCore.QPointF(0,0) - p.boundingRect().center())

def UnclosePolygonF(p):
  n = p.size()
  if n > 1 and p.isClosed():
    p.remove(n-1)
  return p

def IterEdges(p):
  for i in range(1, p.size()):
    yield QLineF(p[i-1], p[i])
  if p.size() > 2 and not p.isClosed():
    yield QLineF(p[p.size()-1], p[0])

def RegularPolygon(sides=6, size=1, r=None, rotate=0.0):
  # Must provide one of size or r, size overrides r
  theta = 2*pi/sides
  if r is None:
    r = sqrt(size*size/(2*(1-cos(theta))))
  rotate = rotate + (pi + theta)/2
  return QPolygonF(map(lambda i: QPointF(r*cos(i*theta+rotate), r*sin(i*theta+rotate))
                      ,range(sides)
                      )
                  )

def RegularPolygram(p,q, size=1):
  'Return a polygram, {p/q}, with p points, visiting every q-th point'
  # p and q should be relatively prime.
  # If p is even, you will only get half of the desired output,
  #   such as a hexagram degenerating to just one if its triangles.
  # If p and q are not relatively prime, you will get a simpler kind of polygon or polygram.
  # Resulting non-degenerate polygons will have holes in them.
  assert q > 0 and p > 0 and q < p # p and q should also be integers
  # Construct a polygram in the manner of string art:
  # First, some nails in the wood:
  boundingPolygon = RegularPolygon(p, size=size)
  # Then start winding the string around, visiting every qth nail.
  vertices = []
  i = 0
  while True:
    vertices.append(boundingPolygon[i])
    i = (i+q) % p
    if i == 0: break
  return QPolygonF(vertices)

def GoldenRectangle(size=1):
  #return QPolygonF(QtCore.QRectF(-.5,.5,size*PHI,1.0)) # renders strangely
  return QPolygonF(( QPointF(-.5+size*PHI,.5)
                   , QPointF(-.5,.5)
                   , QPointF(-.5,-.5)
                   , QPointF(-.5+size*PHI,-.5)
                   ))

def Rhombus(degrees, size=1):
  t = RecordingTurtle().pu().bk(size/2).lt(degrees).bk(size/2).rt(degrees).pd()
  for i in range(2):
    t.fd(size).lt(degrees).fd(size).lt(180-degrees)
  return t.polygon()

def Triangle306090(size=1):
  t = RecordingTurtle().fd(size).lt(90+30).fd(size).fd(size) #.lt(90+60).fd(sqrt(3)*size)
  return RecenteredPolygonF(t.polygon())

def Triangle345(size=1):
  t = RecordingTurtle()
  t.pu().goto(QPointF(-2,-1.5)).pd()
  t.fd(size).fd(size).fd(size)
  t.lt(90)
  t.fd(size).fd(size).fd(size).fd(size)
  t.ltr(pi-asin(3.0/5.0))
  t.fd(size).fd(size).fd(size).fd(size)#.fd(size)
  return t.polygon()

def RightIsoscelesByLegs(size=1):
  'Return a right isosceles triangle whose legs are (size)'
  return RecenteredPolygonF(QPolygonF(( QPointF(0,size), QPointF(0,0), QPointF(size,0) )))

def RightIsoscelesByBase(size=1):
  'Return a right isosceles triangle whose base is (size)'
  size2 = size/2
  return RecenteredPolygonF(QPolygonF(( QPointF(0,0), QPointF(size2,size2), QPointF(size,0) )))

def TangramLargeTriangle(size=1):
  '2-unit-area 45-45-90 triangle including extra vertices bisecting each side'
  t = RecordingTurtle().fd(size).fd(size).lt(90).fd(size).fd(size).lt(90+45).fd(size*sqrt(2)) #.fd(size*sqrt(2))
  return RecenteredPolygonF(t.polygon())

def TangramMediumTriangle(size=1):
  'unit-area 45-45-90 triangle including an extra vertex bisecting the hypotenuse'
  t = RecordingTurtle().fd(size).fd(size).lt(90+45).fd(size*sqrt(2)).lt(90) #.fd(size*sqrt(2))
  return RecenteredPolygonF(t.polygon())

def TangramParallelogram(size=1):
  'unit-area 45-135 parallelogram'
  return RecenteredPolygonF(QPolygonF(( QPointF(0,0), QPointF(size,size), QPointF(size,0), QPointF(0,-size) )))

def TangramPolySet(size=1):
  # All triangles are 45-45-90
  return [ RegularPolygon(sides=4, size=size)  # unit square
         , RightIsoscelesByLegs(size)          # small (half unit area) triangle
         , RightIsoscelesByLegs(size)          # small (half unit area) triangle
         , TangramParallelogram(size)          # unit-area 45-135 parallelogram
         , TangramMediumTriangle(size)
         , TangramLargeTriangle(size)
         , TangramLargeTriangle(size)
         ]

tetriamond_patterns = \
  [ [ [1,1,1,1]
    ]
  , [ [0,1,1,1]
    ,   [1]
    ]
  , [ [1,1,1]
    ,   [1]
    ]
  ]

pentiamond_patterns = \
  [ [ [1,1,1,1,1]
    ]
  , [ [1,1,1,1]
    ,  [0,0,1]
    ]
  , [ [1,1,1,1]
    ,  [1]
    ]
  , [ [0,1,1,1]
    ,   [1,0,1]
    ]
  ]

hexiamond_patterns = \
  [ [ [1,1,1,1,1,1] # parallelogram or bar
    ]
  , [ [0,1,1,1,1,1] # L
    ,   [1]
    ]
  , [ [0,1,1,1,1,1] # mexian hat
    ,   [0,0,1]
    ]
  , [ [1,1,1,1,1]   # sphinx
    ,   [1]
    ]
  , [ [0,1]         # Z or snake
    ,   [1,1,1,1]
    ,   [0,0,1]
    ]
  , [ [1,1,1,1]     # yacht
    ,   [1,0,1]
    ]
  , [ [1,1,1,1]     # bat or chevron
    , [0,0,1,1]
    ]
  , [ [0,0,1,1,1,1] # signpost or pistol
    ,   [0,1,1]
    ]
  , [ [1,1,1,1]     # lobster
    , [1,1]
    ]
  , [ [1,1,0,1]     # hook
    ,   [1,1,1]
    ]
  , [ [0,1,1,1]     # hexagon
    ,   [1,1,1]
    ]
  , [ [0,0,1,1,1]   # butterfly or hourglass
    ,   [0,1,1,1]
    ]
  ]

tetromino_patterns = \
  [ [ [1,1,1,1]
    ]
  , [ [1,1]
    , [1,1]
    ]
  , [ [1,1,1]
    , [0,1,0]
    ]
  , [ [1,1,1]
    , [1,0,0]
    ]
  , [ [1,1,0]
    , [0,1,1]
    ]
  ]

pentomino_patterns = \
  [ [ [0,0,1]
    , [1,1,1]
    , [0,1,0]
    ]
  , [ [1,0,1]
    , [1,1,1]
    ]
  , [ [0,0,0,1]
    , [1,1,1,1]
    ]
  , [ [1,1,1,1,1]
    ]
  , [ [0,1,0,0]
    , [1,1,1,1]
    ]
  , [ [1,0,0]
    , [1,0,0]
    , [1,1,1]
    ]
  , [ [1,1,0]
    , [1,1,1]
    ]
  , [ [1,0,0]
    , [1,1,0]
    , [0,1,1]
    ]
  , [ [0,0,1,1]
    , [1,1,1,0]
    ]
  , [ [1,0,0]
    , [1,1,1] 
    , [0,0,1]
    ]
  , [ [1,1,1]
    , [0,1,0]
    , [0,1,0]
    ]
  , [ [0,1,0]
    , [1,1,1]
    , [0,1,0]
    ] 
  ]

def Segments2QPolygonF(segList):
  '''Given an unordered list of line segments ((x1,y1),(x2,y2)), return an (ordered) QPolygonF.
     Delete converted line segments from list.
     Does not work for disconnected polygons.
  '''
  # Seed list of ordered points with an arbitrary pair of (necessarily adjacent) points
  poly = list(segList.pop())
  # Keep extending list of ordered points by finding the matching line segment
  p = poly[1]
  while segList != []:
    found = False
    for i in range(len(segList)):
      if segList[i][0] == p:
        p = segList[i][1]
        found = True
        break
      elif segList[i][1] == p:
        p = segList[i][0]
        found = True
        break
    if found:
      poly.append(p)
      del segList[i]
    else:
      # This algorithm doesn't work if segments can't be ordered into a single chain
      raise RuntimeError('error converting segments to polygon: segList = {}, poly = {}, p = {}'.format(segList,poly,p))
  return QPolygonF(map(lambda xy: QPointF(*xy), poly))

def TriangleCellScan(trianglemap):
  'Given a rectangular array bitmapping of triangles polyiamond, return a polygon outline of that polyiamond'

  '''
  Interpret a square array as a shear triangle grid:

              (0,0)____________(2,0)
    [              \ a  /\ c  /\ 
      [a,b,c,d]     \  /b \  /d \ 
    ,            =   \/____\/____\(2.5,sqrt(3)/2)
                      \ e  /\ g  /\ 
      [e,f,g,h]        \  /f \  /h \ 
    ]                   \/____\/____\(3,2*sqrt(3)/2)

  '''
  # First, generate unordered line segments (pairs of points) for all on-vs-off borders
  H = sqrt(3)/2
  def get(i,j):
    if i<0 or j<0 or j>=len(trianglemap) or i>=len(trianglemap[j]):
      return 0
    else:
      return trianglemap[j][i]
  segs = []
  for y in range(len(trianglemap)):
    for x in range(len(trianglemap[y])):
      if trianglemap[y][x]:  # for each cell (x,y) that is ON:
        if x%2 == 0:
          # Downward-pointing triangle topl-topr-bot
          (topl, topr, bot) = ( ((x+y)/2,y*H), ((x+y)/2+1,y*H), ((x+y+1)/2,(y+1)*H) )
          if not get(x+1,y-1):  # is upper neighbor ON?
            segs.append( (topl,topr) )  # top edge
          if not get(x-1,y):    # is left neighbor ON?
            segs.append( (topl,bot) )  # left edge
          if not get(x+1,y):    # is right neighbor ON?
            segs.append( (topr,bot) )  # right edge
        else:
          # Upward-pointing triangle top-botl-botr
          (top, botl, botr) = ( ((x+y+1)/2,y*H), ((x+y)/2,(y+1)*H), ((x+y)/2+1,(y+1)*H) )
          if not get(x-1,y+1):  # is lower neighbor ON?
            segs.append( (botl,botr) )  # bottom edge
          if not get(x-1,y):  # is left neighbor ON?
            segs.append( (top,botl) )
          if not get(x+1,y):  # is right neighbor ON?
            segs.append( (top,botr) )
  return segs

def SquareCellScan(squaremap):
  'Given a rectangular array bitmapping of squares for a polyomino, return a polygon outline of that polyomino'
  # First, generate unordered line segments (pairs of points) for all on-vs-off borders
  segs = []
  for y in range(len(squaremap)):
    for x in range(len(squaremap[y])):
      if squaremap[y][x]:  # for each cell (x,y) that is ON:
        if y==0 or not squaremap[y-1][x]:
          segs.append( ((x,y),(x+1,y)) )          # top
        if x==0 or not squaremap[y][x-1]:
          segs.append( ((x,y),(x,y+1)) )          # left
        if x==len(squaremap[y])-1 or not squaremap[y][x+1]:
          segs.append( ((x+1,y),(x+1,y+1)) )      # right
        if y==len(squaremap)-1 or not squaremap[y+1][x]:
          segs.append( ((x,y+1),(x+1,y+1)) )      # bottom
  return segs

def Polyiamond(trianglemap):
  return RecenteredPolygonF(Segments2QPolygonF(TriangleCellScan(trianglemap)))

def Polyomino(squaremap):
  return RecenteredPolygonF(Segments2QPolygonF(SquareCellScan(squaremap)))

def Moniamond(): return Polyiamond([[1]])
def Diamond(): return Polyiamond([[1,1]])
def Triamond(): return Polyiamond([[1,1,1]])
def TetriamondPolySet():
  return (Polyiamond(tp) for tp in tetriamond_patterns)
def PentiamondPolySet():
  return (Polyiamond(pp) for pp in pentiamond_patterns)
def HexiamondPolySet():
  return (Polyiamond(hp) for hp in hexiamond_patterns)

def Monomino(): return Polyomino([[1]])
def Domino(): return Polyomino([[1,1]])
def TriominoPolySet():
  return (Polyomino(tp) for tp in ( [[1,1,1]], [[1,1],[1,0]] ) )
def TetrominoPolySet():
  return (Polyomino(tp) for tp in tetromino_patterns)
def PentominoPolySet():
  return (Polyomino(pp) for pp in pentomino_patterns)

def Arrowhead(size=1):
  "Return a particular concave asymmetrical quadrilateral"
  # note that turtle +y = up while qt +y = down
  t = RecordingTurtle().lt(108).fd(1).lt(144).fd(1).lt(144).fd(.5) #.rt(90).fd(*) implied
  return RecenteredPolygonF(YFlippedPolygonF(t.polygon()))

def HighlightCompliment(c):
  'Calculate a color for drawing a selection highlight to cotrast with c'
  (h,s,v,a) = c.getHsvF()
  h2 = (h+.5) % 1.0     # Pick an opposite hue
  if s < .1 or v < .1:  # If saturation or value is too low (grayish or dark),
    h2 = 1.0/6.0        #   use yellow
  s2 = 1.0
  v2 = 1.0
  return QtGui.QColor.fromHsvF(h2,s2,v2,a)

def BlackOrWhiteCompliment(c):
  'Return either black or white to contrast with c'
  (h,s,v,a) = c.getHsvF()
  if v > .4:
    v2 = 0.0
  else:
    v2 = 1.0
  return QtGui.QColor.fromHsvF(0,0,v2,a)

#==== TileItem classes

'''
QGraphicsItem(parent)
  QAbstractGraphicsShapeItem(parent) - brush, pen
    QGraphicsEllipseItem(rect,parent) - rect, spanAngle, startAngle
    QGraphicsPathItem(path,parent) - path
    QGraphicsPolygonItem(polygon,parent) - fillRule, polygon
    QGraphicsRectItem(rect,parent) - rect
    QGraphicsSimpleTextItem(text,parent) - font, text
  QGraphicsLineItem(line,parent) - line, pen
  QGraphicsPixmapItem(pixmap,parent) - offset, pixmap, shapeMode, transformationMode

Tile(color) : object
  Qt does not support inheritance from more than one Qt class,
    but Python is fine with an (essentially) abstract class calling a method
    it doesn't inherit, as long as derived instances do inherit it.
  provides center of transformation
  provides snap info
  handles mousePress and selection behavior
  provides selection painting data (color)

PolygonTileItem(polygon,parent) : Tile, QGraphicsPolygonItem
  integrates Tile with QGraphicsPolygonItem
  paints selected state
  converts to & from SVG

PenroseTileItem(shape,...,parent) : PolygonTileItem
  paints extra markings
  converts to & from SVG

RulerTileItem(parent) : PolygonTileItem  (or perhaps inherit from RectTileItem?)
  paints extra dynamic markings
  converts to & from SVG

EllipseTileItem() : Tile, QGraphicsEllipseItem
  integrates Tile with QGraphicsEllipseItem
  paints selected state
  converts to & from SVG

'''

#SCENE_MAPPING_CHANGES = frozenset(
#  (QtWidgets.QGraphicsItem.ItemTransformChange
#  ,QtWidgets.QGraphicsItem.ItemPositionChange
#  ,QtWidgets.QGraphicsItem.ItemParentChange
#  ,QtWidgets.QGraphicsItem.ItemRotationChange
#  ,QtWidgets.QGraphicsItem.ItemScaleChange
#  ,QtWidgets.QGraphicsItem.ItemSceneChange
#  ))


'''
PyQt5's classes don't inherit from ABCMeta, so multiple inheritance generates
the error "TypeError: metaclass conflict: the metaclass of a derived class
must be a (non-strict) subclass of the metaclasses of all its bases"
'''
#class Tile(metaclass=ABCMeta):
class Tile(object):
  '''A mixin for QGraphicsItems that can be moved/rotated/scaled by the user
     and can snap to other Tiles'''

  # It's important that this mixin ctor pass posargs up to Qt
  # Extra args should be keywords between posargs and kwargs
  def __init__(self, *posargs, color=None, **kwargs):
    logger.trace('entering')
    super().__init__(*posargs, **kwargs)
    self.setFlags( self.flags()
                 | QtWidgets.QGraphicsItem.ItemIsFocusable
                 | QtWidgets.QGraphicsItem.ItemIsSelectable
                 | QtWidgets.QGraphicsItem.ItemIsMovable
                 | QtWidgets.QGraphicsItem.ItemClipsToShape
               # | QtWidgets.QGraphicsItem.ItemSendsGeometryChanges
                 )
    self._selectionPenWidth = .1
    if color is None: color = QtCore.Qt.yellow
    self.setColor(color)
    #self._drag_type = DRAG_NONE
    #self._drag_timer = QtCore.QElapsedTimer()
    logger.trace('leaving')

  # Defined in derived concrete classes, but not here:
  # @classmethod
  # @abstractmethod ?
  # def newFromSvg(cls, e): pass

  def color(self):
    logger.trace('{}', self._color.getRgb())
    return self._color

  def setColor(self, color):
    self._color = QtGui.QColor(color)
    self.setBrush(self._color)
    self.setPen(QtGui.QPen(QtCore.Qt.black, 0))
    #self.setPen(QtGui.QPen(QtCore.Qt.black, .01))
    self.updateSelectionPen()

  def updateSelectionPen(self):
    #self.selectionPen = QtGui.QPen(QtCore.Qt.red, .2)
    self.selectionPen = QtGui.QPen(HighlightCompliment(self.color()), self._selectionPenWidth)
    self.update()

  #@abstractmethod
  #def snapPoints(self):
  #  logger.warning('abstract method called')
  #  return ()

  def sceneSnapPoints(self):
    # A slower fallback method.
    return (self.mapToScene(p) for p in self.snapPoints())

  def iterLineSegments(self):
    if False:
      yield None

  #def itemChange(self, change, value):
  #  # Note that changes in apparent selection state due to group membership
  #  # do not trigger item selection change notifications!
  #  if change in SCENE_MAPPING_CHANGES:
  #    self._const_sceneSnapPoints = None
  #  return super().itemChange(change, value)

  def setSelected(self, selection):
    g = self.group()
    if selection:
      if not g:
        super().setSelected(True)
        self.scene().selectionGroup.addToGroup(self)
      elif not g is self.scene().selectionGroup:
        logger.warning('selecting item that is not in scene().selectionGroup')
      else:
        super().setSelected(True)
    else:
      if g is self.scene().selectionGroup:
        g.removeFromGroup(self)
        super().setSelected(False)
        self.scene().keepItem(self)
      elif g:
        logger.warning('deselecting item that is not in scene().selectionGroup')
      else:
        super().setSelected(False)

  def mousePressEvent(self, gsMouseEvt):
    # If a TileItem is receiving a mouse click,
    # it is not in the selectionGroup, and presumably not isSelected.
    logger.trace('selecting self')
    if not (gsMouseEvt.modifiers() & QtCore.Qt.ShiftModifier):
      self.scene().clearSelection()
    self.setSelected(True)
    #self.scene().selectionGroup.addToGroup(self)
    #gsMouseEvt.accept()
    logger.trace('now passing event to selectionGroup')
    return self.scene().selectionGroup.mousePressEvent(gsMouseEvt)

class PolygonTileItem(Tile, QtWidgets.QGraphicsPolygonItem):

  def __init__(self, *posargs, polygon=None, **kwargs):
    '''
      Parameters:
      polygon     a QPolygonF, presumably centered around (0,0)
    '''
    # PyQt doesn't support keywords for non-option arguments,
    # so this ctor exists to accept (some of?) them.
    super().__init__(polygon, *posargs, **kwargs)
    # Many Qt functions take const arguments; do likewise here.
    self._const_polygon = polygon
    if QPolygonFArea(polygon) < 1:
      self._selectionPenWidth /= 2
      self.updateSelectionPen()

  @classmethod
  def newFromSvg(cls, e):
    d = svgparsing.ParseSvgAttribs(e)
    if 'points' in d:
      poly = QtGui.QPolygonF(d['points'])
    elif 'd' in d:
      poly = svgparsing.SvgPathCmdsToPolygons(d['d'])[0]
    else:
      poly = None
    pti = cls(polygon = poly)
    if 'fill' in d:
      pti.setColor(QtGui.QColor(*d['fill']))
    if 'transform' in d:
      pti.setTransform(d['transform'])
    return pti

  def toSvg(self, parent):
    # Note that SVG and QTransform matrices are relatively transposed.
    # If no skewing or projection is present, the third vector should be (0,0,1).
    if True:
      pos = self.pos()
      t = self.transform()
    else:
      pos = self.scenePos()
      t = self.sceneTransform().translate(-pos.x(),-pos.y())
    if True:
      t3 = (t.m13(), t.m23(), t.m33())
      if t3 != (0,0,1):
        logger.warning('Loss of transformation: {}', FormatQTransform(t))
    coords = [ '{},{}'.format(p.x(),p.y()) for p in self._const_polygon ]
    #pycode = 'PolygonTileItem(polygon=QPolygonF([{}]))'.format(','.join('QPointF({})'.format(c) for c in coords))
    attrs = \
      { 'points' : ' '.join(coords)
      , 'stroke' : self.pen().color().name()
      , 'stroke-width': '.03px'
      , 'fill' : self.brush().color().name()
      , 'transform' : 'translate({x} {y}) matrix({a} {b} {c} {d} {e} {f})'
     #, 'transform' : 'matrix({a} {b} {c} {d} {e} {f}) translate({x} {y})'
                      .format(a=t.m11(),b=t.m12(),c=t.m21(),d=t.m22(),e=t.m31(),f=t.m32() ,x=pos.x(), y=pos.y())
                     #.format(a=t.m11(),b=t.m21(),c=t.m12(),d=t.m22(),e=t.m13(),f=t.m23() ,x=pos.x(), y=pos.y())
     #, 'tiles:pycode': pycode
      }
    return ET.Element('polygon', attrib=attrs)
    #ET.SubElement(parent, 'polygon', attrib=attrs)

  def snapPoints(self):
    assert len(self._const_polygon) > 2
    return self._const_polygon

  def sceneSnapPoints(self):
    return self.mapToScene(self._const_polygon)

  def iterLineSegments(self):
    poly = self.mapToScene(self._const_polygon)
    z = poly.size()
    for i in range(1, z):
      yield QLineF(poly[i-1], poly[i])
    if z > 2 and not poly.isClosed():
      yield QLineF(poly[z-1], poly[0])

  halfDashedLine = (1,1,1,1)

  def paint(self, painter, option, widget=0):
    #painter.setClipRect(option.exposedRect)
    painter.setPen(self.pen())
    path = QtGui.QPainterPath()
    if logger.isEnabledFor('debug'):
      painter.drawRect(self.boundingRect())  # debug bounding rect
    else:
      # Prevent paint from falling outside the lines
      path.addPolygon(self._const_polygon)
      path.closeSubpath()
      painter.setClipPath(path)
    if self.scene().renderMode != self.scene().RENDER_OUTLINE:
      painter.setBrush(self.brush())
    painter.drawPolygon(self._const_polygon)
    if self.isSelected():
      #painter.setBrush(QtGui.QBrush(QtGui.QColor(255,0,0,191)))
      #self.paintMarchingAnts(painter)
      self.paintInsetHighlight(painter)
    if logger.isEnabledFor('debug'):
      self.paintDebug(painter)

  def paintMarchingAnts(self, painter):
    painter.setBrush(QtCore.Qt.NoBrush)                       # do not re-paint interior
    painter.setPen(QtGui.QPen(QtCore.Qt.white, .10, QtCore.Qt.SolidLine))
    painter.drawPolygon(self._const_polygon)                  # draw solid white border
    dashedPen = QtGui.QPen(QtCore.Qt.black, .10, QtCore.Qt.SolidLine)
    dashedPen.setDashPattern(self.halfDashedLine)             # implicitly sets CustomDashedLine
    dashedPen.setDashOffset(self.scene().marchingAntsOffset)  # make the ants actually march
    dashedPen.setCapStyle(QtCore.Qt.FlatCap)                  # the default SquareCap makes dashes effectively longer
    painter.setPen(dashedPen)
    painter.drawPolygon(self._const_polygon)                  # draw dashed black border

  def paintInsetHighlight(self, painter):
    path = QtGui.QPainterPath()
    path.addPolygon(self._const_polygon)
    path.closeSubpath()
    stroker = QtGui.QPainterPathStroker()
    stroker.setWidth(2.5 * self._selectionPenWidth)
    strokedPath = stroker.createStroke(path).simplified()
    #painter.setPen(QtGui.QPen(HighlightCompliment(self.color()), .1))
    painter.setPen(self.selectionPen)
    painter.setBrush(QtCore.Qt.NoBrush)
    painter.drawPath(strokedPath)

  def paintDebug(self, painter):
    painter.setBrush(QtCore.Qt.NoBrush)
    painter.setPen(QtGui.QPen(QtCore.Qt.gray, .03))
    painter.drawEllipse(QtCore.QPointF(0,0), .05, .05)     # indicate center of rotation
    painter.setPen(QtGui.QPen(QtCore.Qt.green, .03))
    painter.drawEllipse(self._const_polygon[0], .05, .05)  # indicate first vertex
    painter.setPen(QtGui.QPen(QtCore.Qt.cyan, .015))
    for p in self._const_polygon[1:]:
      painter.drawEllipse(p, .025, .025)

  def as_pixmap(self):
    pass

class PenroseTileItem(PolygonTileItem):
  'A PenroseTileItem has special markings (match them to ensure aperiodic tilings)'
  # The order of vertices corresopnds with which markings go where.

  THIN_RHOMB = 0
  THICK_RHOMB = 1
  DART = 2
  KITE = 3

  def __init__(self, *posargs, shape=None, size=1, color=None, polygon=None, **kwargs):
    self._shape = shape
    self._size = size
    if color is None: color = QtGui.QColor.fromHsv(shape*30, 31, 239)
    poly = None
    if not polygon is None:
      poly = polygon
    elif shape == PenroseTileItem.THIN_RHOMB:
      poly = Rhombus(144, size)
    elif shape == PenroseTileItem.THICK_RHOMB:
      poly = Rhombus(72, size)
    elif shape == PenroseTileItem.DART:
      # Draw the kite & dart with outside/longer edges of unit length.
      t = RecordingTurtle().pu().fd(.5*size).pd()
      # Dart: start at arrow-tip and go CCW:
      t.lt(180-36).fd(size).lt(180-36).fd(size/PHI).rt(36).fd(size/PHI) #.lt(180-36).fd(size)
      poly = t.polygon()
    elif shape == PenroseTileItem.KITE:
      t = RecordingTurtle().pu().fd(.5*size).pd()
      t.lt(108).fd(size/PHI).lt(108).fd(size).lt(108).fd(size) #.lt(108).fd(size/PHI)
      logger.trace('RecordingTurtle.vertices() == {}', t.vertices())
      poly = t.polygon()
      logger.trace('poly.isClosed() == {}', poly.isClosed())
      assert len(list(p for p in poly)) == 4
    else:
      raise TypeError("unsupported shape")
    super().__init__(*posargs, polygon=poly, color=color, **kwargs)

  @classmethod
  def newFromSvg(cls, e):
    parsedAttribs = svgparsing.ParseSvgAttribs(e)
    kwargs = { }
    for k in 'tiles:size'.split():
      if k in parsedAttribs: kwargs[k.split(':')[1]] = parsedAttribs[k]
    if 'tiles:shapeno' in parsedAttribs:
      kwargs['shape'] = parsedAttribs['tiles:shapeno']
    if 'points' in parsedAttribs:
      kwargs['polygon'] = QtGui.QPolygonF(parsedAttribs['points'])
      logger.trace('PenroseTileItem.newFromSvg() points = {}', FormatQPointFs(kwargs['polygon']))
    pti = cls(**kwargs)
    if 'fill' in parsedAttribs:
      pti.setColor(QtGui.QColor(*parsedAttribs['fill']))
    if 'transform' in parsedAttribs:
      pti.setTransform(parsedAttribs['transform'])
    return pti

  def toSvg(self, parent):
    e = super().toSvg(parent)
    e.attrib['tiles:type'] = 'PenroseTileItem'
    e.attrib['tiles:shapeno'] = str(self._shape)
    e.attrib['tiles:size'] = str(self._size)
    logger.trace('PenroseTileItem.toSvg() points = {}', e.attrib['points'])
    return e

  def paint(self, painter, option, widget=0):
    super().paint(painter, option, widget)
    painter.setBrush(QtCore.Qt.NoBrush)
    w = .03
    # TODO: generate marking colors from tile colors
    if self._shape == PenroseTileItem.DART or self._shape == PenroseTileItem.KITE:
      c0 = QtGui.QColor.fromHsv(60,255,255)
      c2 = QtGui.QColor.fromHsv(220,255,255)
      r0 = 1 - 1/PHI
      r2 = 1/PHI
      if self._shape == PenroseTileItem.DART:
        (c0,c2) = (c2,c0)
        r2 = r0/PHI
    else: # a rhomb:
      c0 = QtGui.QColor.fromHsv(0,255,255)
      c2 = QtGui.QColor.fromHsv(120,255,255)
      r0 = r2 = (1-1/PHI)/PHI  # arbitrary small fraction of unit
      if self._shape == PenroseTileItem.THICK_RHOMB:
        r2 = 1 - r0
    painter.setPen(QtGui.QPen(c0, w))
    painter.drawEllipse(self.polygon()[0], r0,r0)
    painter.setPen(QtGui.QPen(c2, w))
    painter.drawEllipse(self.polygon()[2], r2,r2)

def UnitFd(t, d):
  'Move turtle t fd in increments of 1 until reaching d'
  while d > 1:
    t.fd(1)
    d -= 1
  if d > 0:
    t.fd(d)
  return t

class RulerTileItem(PolygonTileItem):
  'A RulerTileItem has markings for measuring lengths'

  def __init__(self, *posargs, length=10, width=1, color=None, **kwargs):
    if color is None:
      color = QtGui.QColor.fromHsv(50,127,255)
    t = RecordingTurtle()
    for half in range(2):
      UnitFd(t, length)
      t.lt(90)
      UnitFd(t, width)
      t.lt(90)
    super().__init__(*posargs, polygon=UnclosePolygonF(t.polygon()), color=color, **kwargs)
    self.setFlag(QtWidgets.QGraphicsItem.ItemUsesExtendedStyleOption, True) # for exposedRect
    # ItemCoordinateCache reduces repainting, but turns the lines into
    #   indistinct gray blocks unless logicalCacheSize is big enough,
    #   at which point the ruler somehow becomes invisible.
    #self.setCacheMode(QtWidgets.QGraphicsItem.ItemCoordinateCache, QtCore.QSize(80,80))
    # DeviceCoordinateCache reduces repainting, but only if Item is not rotated/scaled
    #self.setCacheMode(QtWidgets.QGraphicsItem.DeviceCoordinateCache)
    #self.CreateLabelChildren()
    #self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)

  @classmethod
  def newFromSvg(cls, e):
    parsedAttribs = svgparsing.ParseSvgAttribs(e)
    kwargs = { }
    pti = cls(**kwargs)
    if 'fill' in parsedAttribs:
      pti.setColor(QtGui.QColor(*parsedAttribs['fill']))
    if 'transform' in parsedAttribs:
      pti.setTransform(parsedAttribs['transform'])
    return pti

  def toSvg(self, parent):
    e = super().toSvg(parent)
    e.attrib['tiles:type'] = 'RulerTileItem'
    return e

  def setColor(self, color):
    super().setColor(color)
    self._markingsPen = QtGui.QPen(BlackOrWhiteCompliment(self.color()), 0)

  def CreateLabelChildren(self):
    # The point of using TextItems would be to take advantage of ItemIgnoresTransformations
    # However, they would need to be dynamically adjusted, created, destroyed, etc.
    for i in range(1,10):
      label = QtWidgets.QGraphicsSimpleTextItem(str(i), parent=self)
      label.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)
      br = label.boundingRect()
      label.setTransform(QtGui.QTransform.fromTranslate(-br.width()/2, -br.height()/2))
      label.moveBy(i,.5)

  def itemChange(self, change, value):
    if change == QtWidgets.QGraphicsItem.ItemTransformChange:
      xform = value
      abs_scale_x = math.sqrt(xform.m11()**2+xform.m21()**2)
      logger.trace('SCALED {}', abs_scale_x)
      for child in self.childItems():
        br = child.boundingRect()
        child.setTransform(QtGui.QTransform.fromTranslate(-br.width()/2, -br.height()/2)
                                           .scale(abs_scale_x,abs_scale_x))
    return super().itemChange(change,value)

  def paint(self, painter, option, widget=0):
    super().paint(painter, option, widget)
    painter.setPen(self._markingsPen)
    self.paintDecimalLines(painter, option)

  def paintDecimalLines(self, painter, option):
    'Draw decimal tick marks, drawing only those lines that would be usefully visible'
    # typical lod for this program is 32
    world_xform = painter.worldTransform()
    lod = option.levelOfDetailFromTransform(world_xform)
    # font typically defaults to 10 points
    font = painter.font()
    textFlags = QtCore.Qt.AlignCenter | QtCore.Qt.TextDontClip
    textRot = -atan2(world_xform.m12(), world_xform.m22())
    textScale = .02
    magnitude = 0  # 10**0 = units, and go down from there
    maxMagnitude = math.log10(lod/2)
    h = self._const_polygon.boundingRect().height()
    w = self._const_polygon.boundingRect().width()
    n = 0
    #while 10**magnitude * 2 < lod: # draw markings until they're too small
    while magnitude < maxMagnitude:
      dx = 10**(-magnitude)
      # Draw markings every dx, but not actually on the left or right edge of the Ruler.
      # Repaint just the exposed rectangle,
      #   or a bit more to ensure repainting partially clipped text.
      x = max(dx, int(option.exposedRect.left()/dx)*dx)
      xMax = min(w, option.exposedRect.right()+1)
      while x < xMax:
        painter.drawLine(QPointF(x,0),QPointF(x,h))
        painter.drawLine(QPointF(x,1),QPointF(x,1-h))
        if magnitude+.8 < maxMagnitude: #magnitude < 2:
          #font.setPointSize(2)
          #painter.setFont(font)
          ts = textScale * dx
          painter.setWorldTransform(QtGui.QTransform(world_xform).translate(x,h/2).rotateRadians(textRot).translate(-x,-h/2).scale(ts,ts))
          label = '{:.{decimals}f}'.format(x, decimals=magnitude)
          #txrect = QtCore.QRectF(x/ts,0.5/ts,0,0)
          painter.drawText(QtCore.QRectF(x/ts,    h*.5/ts,0,0), textFlags, label)
          if h < 1:
            painter.setWorldTransform(QtGui.QTransform(world_xform).translate(x,1-h/2).rotateRadians(textRot).translate(-x,-(1-h/2)).scale(ts,ts))
            painter.drawText(QtCore.QRectF(x/ts,(1-h*.5)/ts,0,0), textFlags, label)
          painter.setWorldTransform(world_xform)
        x += dx
        n += 1
      magnitude += 1
      h /= 3
      if magnitude > 4: break # performance safety cutoff
    # n should never end up more than half the screen length
    logger.trace('font.pointSize() = {}, textRot = {}, lod = {}, {} lines drawn', font.pointSize(), textRot, lod, n)

  def paintDecimalMarkings(self, painter, option):
    # typical lod for this program is 32
    lod = option.levelOfDetailFromTransform(painter.worldTransform())
    textFlags = QtCore.Qt.AlignCenter | QtCore.Qt.TextDontClip
    font = painter.font()
    font.setPointSize(48)
    painter.setFont(font)
    # Text rendering requires a local coordinate system bigger than 10 or so.
    # Start by effectively expanding local coordinates by 100.
    zbase = .1              # base 10 zoom factor
    zadj = zbase * zbase    # initial zoom adjustment to satisfy font rendering needs
    zinv = 1/zadj
    z = zadj                # z tracks current zoom factor
    painter.scale(z,z)      # initial zoom in
    zmax = zadj/lod
    magnitude = 0           # track exponent for markings scale
    top = h = self._const_polygon.boundingRect().height() * z
    lt = option.exposedRect.left() * z
    rt = option.exposedRect.right() * z
    n = 0
    while z > zmax:
      x = zinv # int(lt)
      while x < 10*zinv: #rt:
        painter.drawLine(QPointF(x,0),QPointF(x,h))
        painter.drawLine(QPointF(x,top),QPointF(x,top-h))
        x += zinv
        n += 1
      txrect = QtCore.QRectF(100,50,0,0)
      painter.drawText(txrect, textFlags, "1")#str(x/10))
      painter.drawEllipse(QPointF(0,0), zinv, zinv)
      #painter.drawEllipse(QPointF(0,0), 10,10)
      #painter.drawEllipse(QPointF(0,0), 100,100)

      # Go to next scale
      painter.scale(zbase,zbase)
      z *= zbase
      magnitude += 1
      top *= z
      h *= z
      lt *= z
      rt *= z
      #h /= 3

      #if magnitude > 4: break # safety cutoff
    # n should never end up more than half the screen length
    logger.trace('lod = {}, {} lines drawn', lod, n)

class EllipseTileItem(Tile, QtWidgets.QGraphicsEllipseItem):

  def __init__(self, rect, *posargs, **kwargs):
    super().__init__(rect, *posargs, **kwargs)
    self._const_rect = rect
    c = rect.center()
    self._const_snapPoints = \
      ( QPointF(rect.right(),c.y())
      , QPointF(c.x(), rect.top())
      , QPointF(rect.left(), c.y())
      , QPointF(c.x(), rect.bottom())
      , c
      )

  @classmethod
  def newFromSvg(cls, e):
    d = svgparsing.ParseSvgAttribs(e)
    if all(a in d for a in 'cx cy rx ry'.split()):
      rect = QtCore.QRectF(d['cx']-d['rx'], d['cy']-d['ry'], d['rx']*2, d['ry']*2)
    else:
      rect = None
    eti = cls(rect=rect)
    if 'fill' in d:
      eti.setColor(QtGui.QColor(*d['fill']))
    if 'transform' in d:
      eti.setTransform(d['transform'])
    return eti

  def toSvg(self, parent):
    pos = self.scenePos()
    t = self.sceneTransform().translate(-pos.x(),-pos.y())
    if True:
      t3 = (t.m13(), t.m23(), t.m33())
      if t3 != (0,0,1):
        logger.warning('Loss of transformation: {}', FormatQTransform(t))
    attrs = \
      { 'cx' : str(self._const_rect.center().x())
      , 'cy' : str(self._const_rect.center().y())
      , 'rx' : str(self._const_rect.width() / 2)
      , 'ry' : str(self._const_rect.height() / 2)
      , 'stroke' : self.pen().color().name()
      , 'stroke-width': '.03px'
      , 'fill' : self.brush().color().name()
      , 'transform' : 'translate({x} {y}) matrix({a} {b} {c} {d} {e} {f})'
     #, 'transform' : 'matrix({a} {b} {c} {d} {e} {f}) translate({x} {y})'
                      .format(a=t.m11(),b=t.m12(),c=t.m21(),d=t.m22(),e=t.m31(),f=t.m32() ,x=pos.x(), y=pos.y())
                     #.format(a=t.m11(),b=t.m21(),c=t.m12(),d=t.m22(),e=t.m13(),f=t.m23() ,x=pos.x(), y=pos.y())
      }
    return ET.Element('ellipse', attrib=attrs)

  def snapPoints(self):
    logger.trace('{}', self._const_snapPoints)
    return self._const_snapPoints

  def paint(self, painter, option, widget=0):
    painter.setPen(self.pen())
    path = QtGui.QPainterPath()
    if logger.isEnabledFor('debug'):
      painter.drawRect(self.boundingRect())  # debug bounding rect
    else:
      # Prevent paint from falling outside the lines
      path.addEllipse(self._const_rect)
      path.closeSubpath()
      painter.setClipPath(path)
    if self.scene().renderMode != self.scene().RENDER_OUTLINE:
      painter.setBrush(self.brush())
    painter.drawEllipse(self._const_rect)
    if self.isSelected():
      #painter.setBrush(QtGui.QBrush(QtGui.QColor(255,0,0,191)))
      painter.setBrush(QtCore.Qt.NoBrush)
      painter.setPen(self.selectionPen)
      n = .25 / 2
      margins = QtCore.QMarginsF(n,n,n,n)
      painter.drawEllipse(self._const_rect.marginsRemoved(margins))
    if logger.isEnabledFor('debug'):
      painter.setBrush(QtCore.Qt.NoBrush)
      painter.setPen(QtGui.QPen(QtCore.Qt.gray, .01))
      for p in self.snapPoints():
        painter.drawEllipse(p, .06,.06)
      painter.setPen(QtGui.QPen(QtCore.Qt.green, .03))
      painter.drawLine(QPointF(0,0), self._const_rect.topLeft())  # indicate "first" vertex
      painter.setPen(QtGui.QPen(QtCore.Qt.blue, .03))
      painter.drawEllipse(QtCore.QPointF(0,0), .05, .05)     # indicate center of rotation

