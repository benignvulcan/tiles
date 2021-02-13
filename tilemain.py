#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
if sys.hexversion < 0x03040000:
  print("Python 3.4 minimum required.")
  sys.exit(2)

import os, math, random, argparse
#from abc import ABCMeta, abstractmethod, abstractclassmethod
import xml.etree.ElementTree as ET

from PyQt5 import QtCore, QtGui, QtWidgets, uic

# DO NOT ENABLE SOUND UNTIL QT STOPS RESETTING ENTIRE SYSTEM VOLUME TO 100% !!!
# This is an issue with at least the following operating systems:
#   * Debian 8
# Sound under Linux is hideously, embarrassingly, shamefully bad.
# Sound support from Qt is pretty shoddy, too.
SOUND = False
if SOUND:
  from PyQt5 import QtMultimedia

import tilelog, tileitems, svgparsing, q2str
from tileitems import PolygonTileItem, PenroseTileItem, RulerTileItem
from tilescene import TileScene
from tileview import TileView

app_version = (0,1)
app_title = 'Magnetic Tiles'
app_about_html = \
u'''<p>Magnetic Tiles version {}.{}
<p>Copyright &copy; 2015&ndash;2016,2021 by Marty White under the GNU GPL V3<p>Python {}'''.format(app_version[0],app_version[1],sys.version.replace('\n','<p>'))

MIME_TYPE_SVG = "image/svg+xml"
XML_decl = '<?xml version="1.0" encoding="utf-8" standalone="no"?>'
DOCTYPE_decl = '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">'
SVG_ns = 'http://www.w3.org/2000/svg'
TILES_ns = 'http://tiles/tiles'
ET_nss = { 'svg' : SVG_ns, 'tiles' : TILES_ns }
SVG_sample = \
'''<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="100" height="100">
  <rect x="0" y="0" width="1" height="1" stroke="#00F" stroke-width=".01" fill="none" />
  <circle cx="0" cy="0" r="1" stroke="black" stroke-width=".01" fill="#FCF" fill-opacity="0.75" />
  <polygon points=".850,.075 .958,.1375 .958,.2625 .850,.325 .742,.2626 .742,.1375" stroke="purple" stroke-width=".03" fill="yellow" />
</svg>
'''
dummySVG = XML_decl + DOCTYPE_decl + SVG_sample

def rename_namespace(doc, from_namespace, to_namespace):
  fnsl = len(from_namespace)
  for elem in doc.getiterator():
      if elem.tag.startswith(from_namespace):
          elem.tag = to_namespace + elem.tag[fnsl:]
      for k in elem.keys():
        if k.startswith(from_namespace):
          v = elem.attrib[k]
          del elem.attrib[k]
          elem.attrib[to_namespace + k[fnsl:]] = v

class SVGReader(object):

  def __init__(self, logger, et=None):
    self._log = logger
    self._et = et
    self._viewXforms = []
    self._items = self.read(et)

  def get_items(self): return self._items
  def get_view_transforms(self): return self._viewXforms

  tiles_types = \
    { 'PolygonTileItem' : PolygonTileItem
    , 'PenroseTileItem' : PenroseTileItem
    , 'RulerTileItem'   : RulerTileItem
    }

  def read(self, e):
    "Given an ElementTree, return a corresponding list of constructed TileItems"
    if 'tiles:type' in e.attrib:
      tt = e.attrib['tiles:type']
    else:
      tt = None
    if tt in self.tiles_types:
      cls = self.tiles_types[tt]
      pti = cls.newFromSvg(e)
      if not pti is None:
        return [pti]
    elif e.tag in 'svg g'.split():
      # Default is to ignore container structure and return the contained objects.
      if tt == 'MagneticTileView':
        # This is not a tile, it's a group for recording the view transformation.
        self._log.trace("found MagneticTileView element")
        if 'transform' in e.attrib:
          self._viewXforms = svgparsing.ParseTransformAttrib(e.attrib['transform'])
      self._log.trace('recursing on "{}" tag', e.tag)
      items = []
      for c in e:
        for it in self.read(c):
          items.append(it)
      return items
    elif e.tag == 'polygon':
      cls = PolygonTileItem
      pti = cls.newFromSvg(e)
      if not pti is None:
        return [pti]
    elif e.tag == 'path':
      if 'd' in e.attrib:
        self._log.trace('path {}', e.attrib['d'])
        pti = PolygonTileItem.newFromSvg(e)
        if not pti is None:
          return [pti]
    elif e.tag == 'ellipse':
      eti = tileitems.EllipseTileItem.newFromSvg(e)
      if not eti is None:
        return [eti]
    return []

regularPolyName = '0-gon monogon digon triangle square pentagon hexagon heptagon octagon nonagon decagon hendecagon dodecagon tridecagon tetradecagon pentadecagon hexadecagon heptadecagon octadecagon nonadecagon icosagon'.split()

#====

from mainWindow_ui import Ui_MagneticTilesMainWindow

INITIAL_VARIANCE = (16,10)

def randomColor():
  return QtGui.QColor.fromHsv(random.randrange(0,360,15), 255, 255)

class MagneticTilesMainWindow(Ui_MagneticTilesMainWindow, QtWidgets.QMainWindow):
  '''A MainWindow supporting use of a TileView (QGraphicsView) onto a
     TileScene (QGraphicsScene) containing magnetic TileItems (QGraphicsItems)
     to interact with.'''
  # Note that the GUI attributes of this class/window are defined in
  # mainWindow.ui (compiled by pyuic to mainWindow_ui.py), edited using Qt Creator:
  #   centralWidget = QWidget()
  #   graphicsView = TileView()
  #   menubar
  #   statusbar
  def __init__(self, logger):
    #QtWidgets.QMainWindow.__init__(self)
    #Ui_MagneticTilesMainWindow.__init__(self)
    super().__init__()
    self._log = logger
    self.setupUi(self)
    self.actionPrint.setVisible(False)
    self.actionSnapSettings.setVisible(False)
    self.actionAboutQt.triggered.connect(QtWidgets.qApp.aboutQt)
    self.initScene()
    self.actionSelectAll.triggered.connect(self.scene.setSelectionAll)
    self.actionDeselectAll.triggered.connect(self.scene.clearSelection)
    self.initGraphicsView()
    self.menuShape.addAction('&Color', self.on_actionShapeColor_triggered)
    self.createShapeAddMenuEntries()
    if self._log.isEnabledFor('debug'): self.actionDebug.setChecked(True)
    self.addBackgroundItems()
    appArgs = QtCore.QCoreApplication.instance().arguments()
    self._log.trace('QCoreApplication.instance().arguments()={}',appArgs)
    self._appdir = os.path.dirname(appArgs[0])
    if len(appArgs) > 1:
      self.open(appArgs[1])
      if len(appArgs) > 2: sef._log.warning('ignoring trailing command-line arguments')
    else:
      self.addInitialTiles()
    if SOUND:
      self.initSound()
      self.scene.snapped.connect(self.playSnapSound)
    self.setWindowModified(False)
    self.updateWindowTitle()
    self._log.trace('returning')

  def initScene(self):
    # Tiles are sized to unit scale, so set scene to show about 20x20 tiles
    # by default.  Unless graphicsView.setSceneRect() is used to override it,
    # the graphicsView will use the scene's rect to calibrate it's scrolling.
    #self.sceneRect = QtCore.QRectF( -10, -10   # origin
    #                              ,  20,  20)  # extent
    # Create scene attribute/object
    self.scene = TileScene(self._log)#self.sceneRect)
    self.scene.setBackgroundBrush(QtGui.QColor.fromHsv(60,5,255))
    #self.scene.changed.connect(self.registerChange)
    self.scene.tileChanged.connect(self.registerChange)

  def initGraphicsView(self):
    self.graphicsView._log = self._log
    self.graphicsView.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
    self.graphicsView.setScene(self.scene)
    self.graphicsView.setAcceptDrops(True)
    self.on_actionViewReset_triggered()

  def newDocument(self):
    self._log.trace('entering')
    self.scene.setSelectionAll()
    self.scene.removeSelection()
    self.on_actionViewReset_triggered()
    self.setWindowFilePath('')
    self.setWindowModified(False)
    self.updateWindowTitle()

  def toss(self, t, pos=None, variance=INITIAL_VARIANCE):
    if pos is None: pos = QtCore.QPointF(0,0)
    if variance and variance != (0,0):
      pos = QtCore.QPointF( random.randrange(-variance[0],variance[0])
                          , random.randrange(-variance[1],variance[1]) )
    t.moveBy(pos.x(), pos.y())
    return t
  def colorize(self, t, color=None):
    if color is None: color = randomColor()
    t.setColor(color)
    return t
  def colorToss(self, t, color=None, pos=None, variance=INITIAL_VARIANCE):
    self.colorize(t, color=color)
    self.toss(t, pos=pos, variance=variance)
    return t
  def addPolygon(self, polygon, color=None, pos=None, variance=None):
    if pos is None:
      #viewRect = self.graphicsView.rect()
      viewRect = self.graphicsView.viewport().rect()
      self._log.trace('view rect = {}', viewRect)
      pos = self.graphicsView.mapToScene(viewRect.center())
      pos = QtCore.QPointF(round(pos.x(),1), round(pos.y(),1))
    self._log.trace('pos={}', pos)
    self.scene.clearSelection()
    it = PolygonTileItem(polygon=polygon, color=color)
    self.colorToss(it, color=color, pos=pos, variance=variance)
    self.scene.addItem(it)
    it.setSelected(True)
    return it
  def addPolygons(self, polygons, color=None, pos=None, variance=(3,3)):
    self.scene.clearSelection()
    tiles = [self.addPolygon(p, color=color, pos=pos, variance=variance) for p in polygons]
    for it in tiles: it.setSelected(True)

  def createShapeAddMenuEntries(self):
    menuRegular = self.menuAdd.addMenu('Regular')
    f = lambda i: lambda: self.addPolygon(tileitems.RegularPolygon(i))
    for sides in range(3,21):
      action = QtWidgets.QAction('{}\t{:2} sides,\t{:.5g}\u00b0'.format(regularPolyName[sides], sides, 360/sides), self)
      action.triggered.connect(f(sides))
      menuRegular.addAction(action)

    menuTriangle = self.menuAdd.addMenu('Triangles')
    menuTriangle.addAction('30\u00B0-60\u00B0-90\u00B0 Right Triangle',
      lambda: self.addPolygon(tileitems.Triangle306090()))
    menuTriangle.addAction('45\u00B0-45\u00B0-90\u00B0 Right Triangle',
      lambda: self.addPolygon(tileitems.RightIsoscelesByLegs()))
    menuTriangle.addAction('60\u00B0-60\u00B0-60\u00B0 Equilateral Triangle',
      lambda: self.addPolygon(tileitems.RegularPolygon(3)))
    menuTriangle.addAction('3-4-5 Pythagorean Right Triangle',
      lambda: self.addPolygon(tileitems.Triangle345()))

    menuQuads = self.menuAdd.addMenu('Quadrilaterals')
    menuQuads.addAction('45\u00B0 Rhombus', lambda: self.addPolygon(tileitems.Rhombus(45)))
    menuQuads.addAction('60\u00B0 Diamond', lambda: self.addPolygon(tileitems.Diamond()))
    menuQuads.addAction('Triamond Trapezoid', lambda: self.addPolygon(tileitems.Triamond()))
    menuQuads.addAction('1/14th Rhombus', lambda: self.addPolygon(tileitems.Rhombus(360/14)))
    menuQuads.addAction('2/14th Rhombus', lambda: self.addPolygon(tileitems.Rhombus(2*360.0/14)))
    menuQuads.addAction('3/14th Rhombus', lambda: self.addPolygon(tileitems.Rhombus(3*360.0/14)))
    menuQuads.addAction('72\u00b0 Thick Rhombus', lambda: self.scene.addItem(PenroseTileItem(shape=1)))
    menuQuads.addAction('144\u00b0 Thin Rhombus', lambda: self.scene.addItem(PenroseTileItem(shape=0)))
    menuQuads.addAction('Dart', lambda: self.scene.addItem(PenroseTileItem(shape=2)))
    menuQuads.addAction('Kite', lambda: self.scene.addItem(PenroseTileItem(shape=3)))
    menuQuads.addAction('Arrowhead\t144\u00b0', lambda: self.addPolygon(tileitems.Arrowhead()))
    menuQuads.addSeparator()
    menuQuads.addAction('Square', lambda:  self.addPolygon(tileitems.RegularPolygon(4)))
    menuQuads.addAction('Golden Rectangle', lambda:
      self.addPolygon(tileitems.GoldenRectangle(), color=QtGui.QColor.fromHsv(55,255,255)))
    menuQuads.addAction('Domino', lambda: self.addPolygon(tileitems.Domino()))

    self.menuAdd.addAction('Pentagram', lambda: self.addPolygon(tileitems.RegularPolygram(5,2)))

    self.menuAdd.addSeparator()

    def addSet(label, f):
      self.menuAdd.addAction(label, lambda: self.addPolygons(f()))

    self.menuAdd.addAction('Diamond 60\u00B0', lambda: self.addPolygon(tileitems.Diamond()))
    self.menuAdd.addAction('Triamond', lambda: self.addPolygon(tileitems.Triamond()))
    addSet('Tetriamond set', tileitems.TetriamondPolySet)
    addSet('Pentiamond set', tileitems.PentiamondPolySet)
    addSet('Hexiamond set', tileitems.HexiamondPolySet)

    self.menuAdd.addSeparator()

    self.menuAdd.addAction('Domino', lambda: self.addPolygon(tileitems.Domino()))
    addSet('Triomino set',  tileitems.TriominoPolySet)
    addSet('Tetromino set', tileitems.TetrominoPolySet)
    addSet('Pentomino set', tileitems.PentominoPolySet)

    self.menuAdd.addSeparator()

    self.menuAdd.addAction('Tangram set', lambda:
      self.addPolygons(tileitems.TangramPolySet(), color=QtCore.Qt.green))

    self.menuAdd.addSeparator()

    self.menuAdd.addAction('Circle\tr=1', lambda:
      self.scene.addItem(tileitems.EllipseTileItem(QtCore.QRectF(-1,-1,2,2))))
    self.menuAdd.addAction('Ellipse\t4/3', lambda:
      self.scene.addItem(tileitems.EllipseTileItem(QtCore.QRectF(-1,-.75,2,1.5))))

    self.menuAdd.addAction('Ruler', lambda: self.scene.addItem(tileitems.RulerTileItem()))

  def addBackgroundItems(self):
    titleItem = QtWidgets.QGraphicsSimpleTextItem(app_title)
    titleItem.setScale(.1)
    titleItem.moveBy(-titleItem.sceneBoundingRect().width()/2, -9)
    titleItem.setBrush(QtGui.QColor.fromHsv(300,5,240))
    titleItem.setPen(QtGui.QPen(QtGui.QColor.fromHsv(300,5,225),0))
    self.scene.addItem(titleItem)

    # Add (non-tile, background) lines
    hLines = [ QtWidgets.QGraphicsLineItem(-10,y,10,y) for y in range(-10,11) ]
    vLines = [ QtWidgets.QGraphicsLineItem(x,-10,x,10) for x in range(-10,11) ]
    circles = [ QtWidgets.QGraphicsEllipseItem(-r,-r,2*r,2*r) for r in range(1,11) ]
    radii   = [ QtWidgets.QGraphicsLineItem(.5*math.cos(r),.5*math.sin(r),10*math.cos(r),10*math.sin(r))
                for r in [math.radians(d) for d in range(0,360,5)] ]
    #lineItems = \
    #  [ QtWidgets.QGraphicsLineItem(-10,  0, 10,0   )  # x axis
    #  , QtWidgets.QGraphicsLineItem(   0,10,   0,-10)  # y axis
    #  , QtWidgets.QGraphicsRectItem(self.scene().sceneRect)    # scene boundary
    #  , QtWidgets.QGraphicsEllipseItem(self.scene().sceneRect) # "calibration" circle
    #  , QtWidgets.QGraphicsRectItem(-.5,-.5,1,1)       # unit square
    #  , QtWidgets.QGraphicsEllipseItem(-.5,-.5,1,1)    # unit circle
    #  ]
    linePen = QtGui.QPen(QtGui.QColor.fromHsv(0,0,239), 0)
    for it in hLines + vLines + circles + radii:
      it.setPen(linePen)
      self.scene.addItem(it)

    zeroLines = [ QtWidgets.QGraphicsLineItem(-.5,0,.5,0)
                , QtWidgets.QGraphicsLineItem(0,-.5,0,.5)
                ]
    for it in zeroLines:
      it.setPen(QtGui.QPen(QtGui.QColor(0,0,0), 0))
      self.scene.addItem(it)

  def addInitialTiles(self):
    # Create some initial tiles
    self.addPolygons(tileitems.TriominoPolySet(), variance=INITIAL_VARIANCE)
    self.addPolygons(tileitems.TetrominoPolySet(), variance=INITIAL_VARIANCE)
    self.addPolygons(tileitems.PentominoPolySet(), variance=INITIAL_VARIANCE)
    self.addPolygons(tileitems.TetriamondPolySet(), variance=INITIAL_VARIANCE)
    self.addPolygons(tileitems.PentiamondPolySet(), variance=INITIAL_VARIANCE)
    self.addPolygons(tileitems.HexiamondPolySet(), variance=INITIAL_VARIANCE)
    self.addPenroseBatch()
    self.addPolygons(tileitems.TangramPolySet(), color=QtCore.Qt.green, variance=INITIAL_VARIANCE)
    self.addRegularPolygons()
    self.addPolygons(list(tileitems.Rhombus(45) for i in range(4)), color=randomColor(), variance=INITIAL_VARIANCE)
    self.addPolygons(list(tileitems.Rhombus(360/14) for i in range(4)), color=randomColor(), variance=INITIAL_VARIANCE)
    self.addPolygons(list(tileitems.Rhombus(2*360.0/14) for i in range(4)), color=randomColor(), variance=INITIAL_VARIANCE)
    self.addPolygons(list(tileitems.Rhombus(3*360.0/14) for i in range(4)), color=randomColor(), variance=INITIAL_VARIANCE)
    self.addMiscellaneousTiles()
    self.scene.clearSelection()

  def addMiscellaneousTiles(self):
    ellipses = [ tileitems.EllipseTileItem(QtCore.QRectF(-1,-1,2,2))
               , tileitems.EllipseTileItem(QtCore.QRectF(-1,-.75,2,1.5)) ]
    for it in ellipses:
      self.colorToss(it)
      self.scene.addItem(it)
    self.addPolygons([tileitems.GoldenRectangle(), tileitems.Arrowhead()], color=QtGui.QColor.fromHsv(55,255,255), variance=INITIAL_VARIANCE)
    self.addPolygons(
      [ tileitems.Triangle306090()
      , tileitems.RightIsoscelesByLegs()
      , tileitems.Triangle345()
      , tileitems.RegularPolygram(5,2)
      , tileitems.Diamond()
      , tileitems.Diamond()
      , tileitems.Triamond()
      , tileitems.Domino()
      , tileitems.Domino()
      ], variance=INITIAL_VARIANCE)

  def addRegularPolygons(self):
    m = 12  # hue modulus
    for i in (3,3,3,3,4,4,5,5,6,6,7,7,8,8,10,12):
      x = PolygonTileItem(polygon=tileitems.RegularPolygon(i))
      #hue = i*(360/m)%360
      #x.setColor(QtGui.QColor.fromHsv(hue, 255, 255))
      x.setColor(randomColor())
      self.toss(x)
      self.scene.addItem(x)

  def addHexagonLetters(self):
    for i in range(26):
      x = PolygonTileItem(polygon=tileitems.RegularPolygon(6))  # Add default hexagon
      hue = i*(360/m)%360
      x.setColor(QtGui.QColor.fromHsv(hue, 255, 255))
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

  def addPenroseBatch(self):
    for shape in range(4):
      for i in range(5):
        it = PenroseTileItem(shape=shape)
        hue = shape*30
        it.setColor(QtGui.QColor.fromHsv(hue, 31, 239))
        self.toss(it)
        self.scene.addItem(it)

  def renderToSvg(self):
    import QtSvg
    svgGen = QtSvg.QSvgGenerator()
    svgGen.setFileName( "output-rendered.svg" )
    svgGen.setSize(QtCore.QSize(20, 20))
    svgGen.setViewBox(QtCore.QRect(0, 0, 10, 10))
    svgGen.setTitle("QtSvgGenerator test render")
    svgGen.setDescription("This window's QGraphicsScene rendered to QtSvgGenerator")
    painter = QtGui.QPainter(svgGen)
    self.scene.render(painter)
    del painter

  def toSvg(self, onlySelected=False):
    'Return selected or all items in the scene as an SVG document string'
    if onlySelected:
      self._log.trace('selectionGroup: pos={}, transform={}'
                     , self.scene.selectionGroup.pos()
                     , q2str.FormatQTransform(self.scene.selectionGroup.transform()) )
    svg_attribs = \
      { 'xmlns'       : SVG_ns
      , 'xmlns:tiles' : TILES_ns
      , 'version'     : '1.1'
      , 'width'       : str(self.scene.sceneRect().width())
      , 'height'      : str(self.scene.sceneRect().height())
      }
    doc = ET.Element('svg', attrib=svg_attribs)
    svg_xlate = 'translate({x} {y})'.format( x=self.graphicsView.horizontalScrollBar().value()
                                           , y=self.graphicsView.verticalScrollBar().value() )
    svg_matrix = q2str.FormatQTransformSVGMatrix(self.graphicsView.transform())
    scene_g = ET.SubElement(doc, 'g', transform='{} {}'.format(svg_xlate, svg_matrix))
    scene_g.attrib['tiles:type'] = 'MagneticTileView'
    for it in self.scene.items(order=QtCore.Qt.AscendingOrder):
      if it.isSelected() or not onlySelected:
        if hasattr(it, 'toSvg'):
          e = it.toSvg(scene_g)
          scene_g.append(e)
    contents = '\n'.join([XML_decl] + ET.tostringlist(doc, encoding='unicode'))
    self._log.trace('{}', contents)
    return contents

  def fromSvg(self, svg):
    #etdoc = ET.parse(io.StringIO(svg))
    #doc = etdoc.getroot()
    doc = ET.fromstring(svg)
    #self._log.debug('dir({}) = {}', doc.__class__, dir(doc))
    #remove_namespace(doc, SVG_ns)
    rename_namespace(doc, u'{%s}'%SVG_ns, '')
    rename_namespace(doc, u'{%s}'%TILES_ns, 'tiles:')
    #def dump(t, indent=''):
    #  self._log.trace('{}{}: {}', indent, t.tag, t.attrib)
    #  for s in t: dump(s, indent+'  ')
    #dump(doc)
    #def search(p):
    #  #self._log.trace('searching "{}":', p)
    #  for e in doc.findall(p): #, namespaces=ET_nss):
    #    dump(e)
    #search('polygon')
    #search('svg:polygon')
    #search('{http://www.w3.org/2000/svg}polygon')
    #search('.')
    #search('svg')
    reader = SVGReader(self._log, doc)
    items = reader.get_items()
    for it in items:
      self.scene.addItem(it)
      #it.setSelected(True)
    if False: #reader.get_view_transforms():
      self._log.trace("loading view transform from SVG")
      self.graphicsView.setTransform( QtGui.QTransform(), combine=False )
      hbar = self.graphicsView.horizontalScrollBar()
      vbar = self.graphicsView.verticalScrollBar()
      for t in reversed(reader.get_view_transforms()):
        if t.type() == QtGui.QTransform.TxTranslate:
          hbar.setValue(hbar.value() + t.m31())
          vbar.setValue(hbar.value() + t.m32())
        else:
          self.graphicsView.setTransform(t, combine=True)
    return items

  @QtCore.pyqtSlot()
  def registerChange(self, what=None):
    self._log.debug('changed')
    self.setWindowModified(True)

  @QtCore.pyqtSlot()
  def on_actionCopy_triggered(self):
    self._log.debug("actionCopy_triggered")
    #QtWidgets.QApplication.clipboard().setText("just a plain string", QtGui.QClipboard.Clipboard)
    mimedata = QtCore.QMimeData()
    #mimedata.setData(MIME_TYPE_SVG, self.toSvg(onlySelected=True)) # "arg 2 unexpected type 'str'" under CygWin
    mimedata.setData(MIME_TYPE_SVG, self.toSvg(onlySelected=True).encode())
    QtWidgets.QApplication.clipboard().setMimeData(mimedata)

  @QtCore.pyqtSlot()
  def on_actionDelete_triggered(self):
    self._log.debug("actionDelete_triggered")
    self.scene.removeSelection()

  @QtCore.pyqtSlot()
  def on_actionCut_triggered(self):
    self._log.debug("actionCut_triggered")
    self.on_actionCopy_triggered()
    self.on_actionDelete_triggered()

  @QtCore.pyqtSlot()
  def on_actionPaste_triggered(self):
    self._log.debug("actionPaste_triggered")
    mimedata = QtWidgets.QApplication.clipboard().mimeData()
    for mt in ["image/svg+xml", "image/x-inkscape-svg"]:
      if mimedata.hasFormat(mt):
        md = mimedata.data(mt)
        self._log.debug("type(mime data) == {}", type(md))
        try:
          open('tiles-debug-pasted-mimedata.svg','wb').write(md)
        except:
          pass
        self.scene.clearSelection()
        items = self.fromSvg(md)
        for it in items:
          it.setSelected(True)
        break
    else:
      self._log.debug("mimedata.formats() = {}", mimedata.formats())

  def readyToClose(self):
    'Ensure no data is lost: Return True, unless the document was modified and the user hits cancel'
    if self.isWindowModified():
      stdBtnId = QtWidgets.QMessageBox.warning(self, 'Save file?',
        'This document has been modified.\nDo you want to save your changes?',
        QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel)
      if stdBtnId == QtWidgets.QMessageBox.Save:
        return self.on_actionSave_triggered()
      elif stdBtnId == QtWidgets.QMessageBox.Cancel:
        return False
    return True

  @QtCore.pyqtSlot()
  def on_actionSave_triggered(self):
    self._log.debug("actionSave_triggered")
    if not self.windowFilePath():
      return self.on_actionSaveAs_triggered()
    self.saveTo(self.windowFilePath())
    return True

  @QtCore.pyqtSlot()
  def on_actionSaveAs_triggered(self):
    self._log.debug("actionSaveAs_triggered")
    name = self.getSaveFileName()
    if name:
      if self.saveTo(name):
        self.setSaveFileName(name)
        return True
    return False

  def getSaveFileName(self):
    (name, selectedFilter) = QtWidgets.QFileDialog.getSaveFileName(self,
      filter="SVG files (*.svg)",
      options=QtWidgets.QFileDialog.HideNameFilterDetails)
    if name:
      if not name.lower().endswith('.svg'):
        name = name + '.svg'
      if os.path.exists(name):
        stdBtnId = QtWidgets.QMessageBox.question(self, 'Overwrite file?',
          'A file named "{}" already exists.  Are you sure you want to overwrite it?'.format(name))
        if stdBtnId != QtWidgets.QMessageBox.Yes:
          name = ''
    return name

  def setSaveFileName(self, name):
    self.setWindowFilePath(name)
    self.updateWindowTitle()

  def updateWindowTitle(self):
    # \u2014 = em dash
    if self.windowFilePath():
      title = '{}[*] \u2014 {}'.format(os.path.basename(self.windowFilePath()), app_title)
    else:
      title = app_title + '[*]'
    self.setWindowTitle(title)

  def saveTo(self, filename):
    try:
      f = open(filename, 'wt')
    except:
      QtWidgets.QMessageBox.critical(self, 'Error', 'Error opening {}'.format(filename))
      return False
    if not f:
      return False
    contents = self.toSvg()
    try:
      f.write(contents)
      f.close()
    except:
      QtWidgets.QMessageBox.critical(self, 'Error', 'Error writing {}'.format(filename))
      return False
    self._log.info('saved to {}', filename)
    self.setWindowModified(False)
    self.updateWindowTitle()
    return True

  @QtCore.pyqtSlot()
  def on_actionOpen_triggered(self):
    self._log.debug("actionOpen_triggered")
    if self.readyToClose():
      (name, _selectedFilter) = QtWidgets.QFileDialog.getOpenFileName(self, filter="SVG files (*.svg)")
      if name:
        self.open(name)

  def open(self, name):
    self.newDocument()
    try:
      f = open(name)
    except FileNotFoundError:
      QtWidgets.QMessageBox.critical(self, 'Error', 'File not found: {}'.format(name))
      return
    self.fromSvg(f.read())
    self.setSaveFileName(name)
    self.setWindowModified(False)
    self.updateWindowTitle()

  @QtCore.pyqtSlot()
  def on_actionFileNew_triggered(self):
    self._log.debug('actionFileNew_triggered')
    if self.readyToClose():
      self.newDocument()

  @QtCore.pyqtSlot()
  def on_actionPrint_triggered(self):
    self._log.debug('actionPrint_triggered')

  @QtCore.pyqtSlot()
  def on_actionShapeAdd_triggered(self):
    self._log.debug('actionShapeAdd_triggered')

  @QtCore.pyqtSlot()
  def on_actionShapeReset_triggered(self):
    self._log.debug('actionShapeReset_triggered')
    self.scene.selectionGroup.resetShapes()

  @QtCore.pyqtSlot()
  def on_actionShapeMirror_triggered(self):
    self._log.debug('actionShapeMirror_triggered')
    self.scene.selectionGroup.mirror()

  @QtCore.pyqtSlot()
  def on_actionShapeColor_triggered(self):
    self._log.debug('actionShapeColor_triggered')
    self.scene.selectionGroup.editColor()

  @QtCore.pyqtSlot(bool)
  def on_actionSnapObjects_toggled(self, newValue):
    self._log.debug('actionSnapObjects_toggled')
    self.scene.snapToTilesEnabled = not self.scene.snapToTilesEnabled

  @QtCore.pyqtSlot(bool)
  def on_actionSnapAngles_toggled(self, newValue):
    self._log.debug('actionSnapAngles_toggled')
    self.scene.snapToAnglesEnabled = not self.scene.snapToAnglesEnabled

  @QtCore.pyqtSlot()
  def on_actionSnapSettings_triggered(self):
    self._log.debug('actionSnapSettings_triggered')

  @QtCore.pyqtSlot()
  def on_actionViewReset_triggered(self):
    self._log.debug('actionViewReset_triggered')
    self.graphicsView.resetTransformPy()

  @QtCore.pyqtSlot(bool)
  def on_actionOutline_toggled(self, newValue):
    self._log.debug('Outline_toggled')
    if self.scene.renderMode is self.scene.RENDER_OUTLINE:
      self.scene.renderMode = self.scene.RENDER_PLAIN
    else:
      self.scene.renderMode = self.scene.RENDER_OUTLINE
    self.scene.invalidate()

  def initSound(self):
    if SOUND:
      self._log.warning('Setting up sound, system volume may go to 100% ... COVER YOUR EARS')
      url = QtCore.QUrl.fromLocalFile(os.path.abspath('resources/click1.wav'))
      if url.isValid():
        self._click1 = QtMultimedia.QSoundEffect(self)
        self._click1.setSource(url)
        #self._click1.setVolume(1.0) # sets system volume!!

  @QtCore.pyqtSlot()
  def playSnapSound(self):
    if SOUND:
      self._click1.setLoopCount(1)
      self._click1.play()

  @QtCore.pyqtSlot(bool)
  def on_actionFullscreen_toggled(self, _newValue):
    self.setWindowState(self.windowState() ^ QtCore.Qt.WindowFullScreen)

  @QtCore.pyqtSlot(bool)
  def on_actionDebug_toggled(self, newValue):
    if newValue:
      self._log.setFilterLevel('trace')
    else:
      self._log.setFilterLevel('info')
    self._log.debug('actionDebug_toggled')
    self.scene.update()

  @QtCore.pyqtSlot()
  def on_actionHelpHelp_triggered(self):
    helpFile = os.path.abspath(os.path.join(self._appdir,'docs','help.html'))
    helpUrl = QtCore.QUrl.fromLocalFile(helpFile)
    self._log.debug('{}', helpFile)
    self._log.debug('{}', helpUrl)
    if not QtGui.QDesktopServices.openUrl(helpUrl):
      self._log.warning('Failed to launch help browser')
      QtWidgets.QMessageBox.critical(self, 'Error', 'Failed to open {}'.format(helpFile))

  @QtCore.pyqtSlot()
  def on_actionAbout_triggered(self):
    QtWidgets.QMessageBox.about(self, app_title, app_about_html)

  def closeEvent(self, evt):
    if self.readyToClose():
      evt.accept()
    else:
      evt.ignore()

def main(argv):
  logger = tilelog.NotLogger()
  tileitems.logger = logger
  svgparsing.logger = logger
  p = argparse.ArgumentParser()
  p.add_argument('--call') # call the named member of mainWnd and exit
  p.add_argument('--debug', action='store_true')
  p.add_argument('--trace', action='store_true')
  opts, argv_remaining = p.parse_known_args()
  if opts.debug: logger.setFilterLevel('debug')
  if opts.trace: logger.setFilterLevel('trace')
  logger.debug(str(opts))
  #ET.register_namespace('',SVG_ns)
  #ET.register_namespace('tiles',TILES_ns)
  app = QtWidgets.QApplication(argv[:1] + argv_remaining)
  mainWnd = MagneticTilesMainWindow(logger)
  mainWnd.show()
  if not opts.call is None:
    f = getattr(mainWnd, opts.call)
    rc = f()
    if not isinstance(rc, int): rc = 0
    #mainWnd.close()
    #app.exit(rc)
  else:
    rc = app.exec_()
  # WORKAROUND: PyQt 4.7.2 frequently segfaults if the QApplication instance
  #   is garbage collected too soon (e.g., if it is not a global variable on
  #   exiting).
  global persistent_app
  persistent_app = app

if __name__=='__main__': sys.exit(main(sys.argv))
