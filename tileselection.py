#!/usr/bin/env python3

import os, math, unittest
from PyQt5 import QtCore, QtGui, QtWidgets
from q2str import *

# TODO:
#   Fix so that multiple types of transformation can happen
#     while dragging, for example:
#     user translates with mouse while rotating with keyboard
#     but then hits ESC to cancel both transforms
#   Draw dragging indicators:
#     rotate & scale center of transformation
#     distance line/arrow ?
#     distance, angle, scale factor ?

def isCloseQPointF(p, q, rel_tol=1e-09, abs_tol=0.0):
  # Modeled after Python 3.5 isclose() function.
  '''Return True if both x and y ordinates are correspondingly close;
     does not consider pythagorean or manhattan distance.'''
  pq = p - q
  return ( abs(pq.x()) <= max(rel_tol * max(abs(p.x()), abs(q.x())), abs_tol)
       and abs(pq.y()) <= max(rel_tol * max(abs(p.y()), abs(q.y())), abs_tol)
         )

class TestIsCloseQPointF(unittest.TestCase):
  def test_IsCloseQPointF(self):
    p = QtCore.QPointF(5.2, -7.8)
    q = QtCore.QPointF(-1.5, 0.4)
    self.assertTrue(isCloseQPointF(p, p))
    self.assertTrue(isCloseQPointF(q, q))
    self.assertFalse(isCloseQPointF(p, q))
    self.assertFalse(isCloseQPointF(p, p + QtCore.QPointF(-1e-7, 1e-7)))
    self.assertFalse(isCloseQPointF(q, q + QtCore.QPointF(-1e-7, 1e-7)))
    self.assertTrue(isCloseQPointF(p, p + QtCore.QPointF(-1e-10, 1e-10)))
    self.assertTrue(isCloseQPointF(q, q + QtCore.QPointF(-1e-10, 1e-10)))
    self.assertFalse(isCloseQPointF(p, p + QtCore.QPointF(-1e-7, 1e-10)))
    self.assertFalse(isCloseQPointF(q, q + QtCore.QPointF(-1e-7, 1e-10)))

def uniq(seq, key=None): 
   'A fairly fast order-preserving uniq'
   # http://www.peterbe.com/plog/uniqifiers-benchmark
   if key is None:
     def key(x): return x
   seen = {}
   result = []
   for item in seq:
       marker = key(item)
       if marker in seen: continue
       seen[marker] = 1
       result.append(item)
   return result

def _ClosestPair(ps, qs):
  'Assuming points are already sorted, find point in ps closest to point in qs'
  assert ps and qs
  if len(ps) == 1 and len(qs) == 1:
    pq = ps[0] - qs[0]
    return (pq.x()**2 + pq.y()**2, p, q)
  psMed = int(len(ps)//2)
  qsMed = int(len(qs)//2)
  (psLeft, psRight) = (ps[:psMed], ps[psMed:])
  (qsLeft, qsRight) = (qs[:qsMed], qs[qsMed:])
  (pqL, pL, qL) = ClosestPairPresorted(psLeft, qsLeft)
  (pqR, pR, qR) = ClosestPairPresorted(psRight, qsRight)
  #if pqL <= pqR:
  #  (pq, p, q) = (pqL, pL, qL)
  #else:
  #  (pq, p, q) = (pqR, pR, qR)
  #for p in psLeft: # use bisect() to find points closer than pqL or pqR

def QPFKey(p): return (p.x(), p.y())

def ClosestPair(ps, qs):
  if not ps or not qs: return None
  ps = sorted(uniq(ps, QPFKey), key=QPFKey)
  qs = sorted(uniq(qs, QPFKey), key=QPFKey)
  return _ClosestPair(ps, len(ps), qs, len(qs))

def pathVertices(path):
  en = path.elementCount()
  pts = [QtCore.QPointF(e.x, e.y) for e in (path.elementAt(i) for i in range(en))]
  #self._log.trace('{}: [{}]', en, FormatQPointFs(pts))
  return pts

# Constants for different dragging states
DRAG_NONE   = 0
DRAG_XLATE  = 1
DRAG_ROTATE = 2
DRAG_SCALE  = 3

def mapDragButton(button):
  if   button == QtCore.Qt.LeftButton  : return DRAG_XLATE
  elif button == QtCore.Qt.RightButton : return DRAG_ROTATE
  elif button == QtCore.Qt.MiddleButton: return DRAG_SCALE
  else: return DRAG_NONE

# QKeyEvent.key() provides no clue about shifted digit keys.
# QKeyEvent.nativeVirtualKey() provides no clue about shifted digit keys.
# QKeyEvent.nativeScanCode() flat doesn't work on a Mac.
# Fuck knows how to do this in a language/keyboard independent fashion.
# Are there really millions of keyboards in some country that don't do shifted digits?
# Probably should use Alt instead of shift.
shiftDigitKeyMap = \
  { QtCore.Qt.Key_ParenRight  : 0
  , QtCore.Qt.Key_Exclam      : 1
  , QtCore.Qt.Key_At          : 2
  , QtCore.Qt.Key_NumberSign  : 3
  , QtCore.Qt.Key_Dollar      : 4
  , QtCore.Qt.Key_Percent     : 5
  , QtCore.Qt.Key_AsciiCircum : 6
  , QtCore.Qt.Key_Ampersand   : 7
  , QtCore.Qt.Key_Asterisk    : 8
  , QtCore.Qt.Key_ParenLeft   : 9
  }

def _snapKey(s): # sort key for snap tuples
  return ( s[1].x(),s[1].y(), s[2].x(),s[2].y() )

class SelectionGroup(QtWidgets.QGraphicsItemGroup):
  'A selection of TileItems that is being transformed.'
  # It is not a TileItem, because it doesn't need to be.

  def __init__(self, logger, parent=None):
    self._shape = None
    self._log = logger
    super().__init__(parent=parent)
    self.setFlags( self.flags()
                 | QtWidgets.QGraphicsItem.ItemIsFocusable
                 | QtWidgets.QGraphicsItem.ItemIsSelectable
                 | QtWidgets.QGraphicsItem.ItemIsMovable
                #| QtWidgets.QGraphicsItem.ItemClipsToShape
                 | QtWidgets.QGraphicsItem.ItemSendsGeometryChanges
                 )
    self._drag_timer = QtCore.QElapsedTimer()
    self._nearSnapsDebug = None
    self.initDragXform()

  def initDragXform(self):
    self._drag_type = DRAG_NONE
    self._base_xform = self.transform()
    self._drag_xlate = QtCore.QPoint()
    self._drag_rotate = 0
    self._drag_scale = 1
    self._drag_mirror = 1
    self.computeSceneXformCenter()

  def computeSceneXformCenter(self):
    self._sceneXformCenter = self.sceneBoundingRect().center()

  def editColor(self):
    n = 0
    firstColor = None
    heterogeneous = False
    (r,g,b) = (0,0,0)
    for it in self.childItems():
      self._log.trace('{}', it)
      c = it.color().convertTo(QtGui.QColor.Rgb)
      if firstColor is None:
        firstColor = c
      elif firstColor != c:
        heterogeneous = True
      r += c.red()
      g += c.green()
      b += c.blue()
      n += 1
    if n:
      r = float(r)/n
      g = float(g)/n
      b = float(b)/n
      c = QtGui.QColor(r,g,b)
      # Under WinDOS 7, I can only get the retarded system/native dialog with:
      #   - no indication of previous color as compared with selected color
      #   - no visual display of alpha channel, just the numeric spinner!
      c2 = QtWidgets.QColorDialog.getColor( c
             , parent=self.scene().parent()
             , options=QtWidgets.QColorDialog.ShowAlphaChannel )
        #|QtWidgets.QColorDialog.DontUseNativeDialog)
      if c2.isValid() and (c2 != c or heterogeneous):
        for it in self.childItems():
          it.setColor(c2)
        self.scene().tileChanged.emit()

  def autoscale(self):
    'Scale the selection so as to make at least some lines unit length.'
    # Pasting a star from Inkscape 0.92, the equilateral sides are only about 7 digits equal.
    REL_TOL=1e-6
    d = {}
    for it in self.childItems():
      for e in it.iterLineSegments():
        n = e.length()
        if math.isclose(n, 1.0, rel_tol=REL_TOL):
          return
        elif not math.isclose(n, 0.0, rel_tol=REL_TOL):
          for k in d:
            if math.isclose(n, k, rel_tol=REL_TOL):
              d[k] += 1
              n = None
              break
          if not n is None:
            d[n] = d.get(n, 0) + 1
    counts = sorted(d.items(), key=lambda it: (it[1],-it[0]))
    self._log.trace('counts = {}', counts)
    if counts:
      self._drag_scale = 1/counts[-1][0]
      self.applyDragXforms()

  def shape(self):
    "Return QPainterPath (in Item coordinates) for collision/hit testing"
    if self._shape is None:
      self._shape = QtGui.QPainterPath()
      i = 0
      for it in self.childItems():
        self._shape.addPath(self.mapFromItem(it, it.shape()))
        i += 1
      self._shape.closeSubpath()
      self._log.trace('{} children in shape', i)
    return QtGui.QPainterPath(self._shape)

  def flushShape(self):
    self.prepareGeometryChange()
    self._shape = None

  def resetTransforms(self):
    'Reset all transformations.  Be sure to call this when clearing the selection'
    self._log.trace('{} children', len(self.childItems()))
    self.resetTransform()
    self.setPos(0,0)
    self.flushShape()
    self._log.trace('returning')

  def normalizeTransforms(self):
    self.prepareGeometryChange()
    children = self.childItems()
    for it in children:
      self.removeFromGroup(it)
    self.resetTransforms()
    for it in children:
      self.addToGroup(it)

  #def snapShape(self):
  #  "Return QPainterPath (in Item coordinates) for snapping"
  #  return self.shape()

  def resetShapes(self):
    # Qt BUG: QGraphicsItemGroup caches bounding rectangle and only updates
    #         it during addToGroup() and removeFromGroup() !
    if not self._drag_type is DRAG_NONE:
      self.cancelDrag()
    self.prepareGeometryChange()
    self._log.trace('{} children', len(self.childItems()))
    for it in self.childItems():
      it.resetTransform()
      it.setPos(0,0)
      self.removeFromGroup(it)
      self.addToGroup(it)
    self.resetTransforms()
    self._log.trace('emitting tileChanged')
    self.scene().tileChanged.emit()

  def addToGroup(self, item):
    super().addToGroup(item)
    self.computeSceneXformCenter()

  def removeFromGroup(self, item):
    n = len(self.childItems())
    super().removeFromGroup(item)
    if n: assert len(self.childItems()) == n-1
    #self.resetTransforms()
    self.computeSceneXformCenter() # this doesn't change anything!

  def mirror(self):
    self._drag_mirror = -self._drag_mirror
    self.applyDragXforms()

    #ctr = self.sceneBoundingRect().center()
    #self._log.trace('transformOriginPoint = {}, center = {}', self.transformOriginPoint(), ctr)
    #xform = QtGui.QTransform.fromTranslate(ctr.x(),ctr.y()).scale(-1,1).translate(-ctr.x(),-ctr.y())
    #self.setTransform(self.transform() * xform)

    self.scene().tileChanged.emit()

  def nearestSnaps(self, snap_dist, excludePt=None):
    '''Return a list of (equally) closest snap-tuples, in scene coordinates.
       Parameters are in scene coordinates.
       Returned tuples are (distance squared, QPointF p from self, QPointF q from other)
    '''
    # This never seems to take more than a couple dozen ms, but nevertheless
    # performance is very sluggish, because Qt5 sends all mouse events
    # without compression no matter how long it takes to respond.
    search_timer = QtCore.QElapsedTimer()
    search_timer.start()
    snap_margins = QtCore.QMarginsF(snap_dist*1.001,snap_dist*1.001,snap_dist*1.001,snap_dist*1.001)
    nearest_dist2 = snap_dist ** 2         # Use squared distances to avoid calling sqrt
    nearest = []  # list of nearby pairs of points
    # It's distinctly faster to let QGraphicsScene compare each child tile with
    # other tiles than to ask it to compare all child points with other tiles,
    # though this still ends up O(n*n) when dragging many tiles over many tiles.
    for child in self.childItems():
      snap_search_rect = child.sceneBoundingRect().marginsAdded(snap_margins)
      nearby_items = self.scene().items(snap_search_rect)
      nearby_tiles = [it for it in nearby_items if hasattr(it, "sceneSnapPoints") and not it.isSelected()]
      if nearby_tiles:
        self._log.trace('{} nearby tiles', len(nearby_tiles))
        for other_tile in nearby_tiles:
          for p in child.sceneSnapPoints():
            assert isinstance(p, QtCore.QPointF)
            if excludePt is None or QtCore.QLineF(p, excludePt).length() > snap_dist/100.0:
              for q in other_tile.sceneSnapPoints():
                assert isinstance(q, QtCore.QPointF)
                if excludePt is None or QtCore.QLineF(q, excludePt).length() > snap_dist/100.0:
                  pq = q - p
                  pq2 = pq.x()**2 + pq.y()**2
                  if pq2 <= nearest_dist2:
                    #assert pq.x() <= snap_dist
                    #assert pq.x() >= -snap_dist
                    #assert pq.y() <= snap_dist
                    #assert pq.y() >= -snap_dist
                    if pq2 < nearest_dist2:
                      nearest_dist2 = pq2
                      nearest = []
                      # TODO: shrink snap_margins ?
                    assert isinstance(q, QtCore.QPointF)
                    # ** BUGFIX **
                    # There appears to be a bug such that if I do not make a copy of q here,
                    # it sometimes mysteriously changes by the end of the function.
                    # Bug was seldom if ever visible under Linux, Windows, or OS 10.10
                    # Debugged under OS X 10.14, Python 3.8.3, PyQt 5.15.2, 2021-Feb
                    nearest.append( (pq2, QtCore.QPointF(p), QtCore.QPointF(q)) )
                    #self._log.trace('nearest = {}', nearest)
      if search_timer.hasExpired(250):
        self._log.info('aborting slow search: {} ms', search_timer.elapsed())
        return []
    #self._log.info('{} children searched in {} ms', len(self.childItems()), search_timer.elapsed())
    #self._log.trace('final nearest = {}', nearest)
    #for pq2,p,q in nearest:
    #  assert isinstance(p, QtCore.QPointF)
    #  assert isinstance(q, QtCore.QPointF)
    #  pq = q - p
    #  assert pq.x() <= snap_dist
    #  assert pq.x() >= -snap_dist
    #  assert pq.y() <= snap_dist
    #  assert pq.y() >= -snap_dist
    return nearest

  def snapToShapesByXlation(self):
    '''Snap (by translating self.transform()) to the nearest other Tile snap point
       (if within snapDist).  Return the snap QPointF.
    '''
    assert self.scene().snapDist >= 0
    assert self.transformations() == []
    assert self.rotation() == 0 and self.scale() == 1
    nearSnaps = self.nearestSnaps(self.scene().snapDist)
    self._nearSnapsDebug = None
    if nearSnaps:
      self._nearSnapsDebug = nearSnaps
      #self._log.trace('snapDist {}: {} snaps', self.scene().snapDist, len(nearSnaps))
      self.scene().snapped.emit()
      nearSnaps.sort(key=_snapKey)  # ensure repeatable ordering of points
      # Pick an arbitrary snap; move self's p to concide with other's q
      pq2, p, q = nearSnaps[0]
      snapDelta = q - p  # if target q is greater, snapDelta from p will be positive
      self._log.trace('snap dist={}, snapDelta x={}, y={}', self.scene().snapDist, snapDelta.x(), snapDelta.y())
      #self._log.trace('snap-translating {} from {} to {}', snapDelta, p, q)
      #scene_xform.translate(snapDelta.x(), snapDelta.y())
      #self.setTransform(self._base_xform * scene_xform)
      self.setTransform(self.transform().translate(snapDelta.x()*self._drag_mirror, snapDelta.y()))
      return q

  def snapToShapesByRotation(self, q):
    '''Snap (by rotating self.transform() about q) to the nearest other Tile snap point
       (if within snapDist).  Return the snap QPointF.
    '''
    nearSnaps2 = self.nearestSnaps(self.scene().snapDist, excludePt=q)
    if nearSnaps2:
      nearSnaps2.sort(key=_snapKey)
      pq22, p2, q2 = nearSnaps2[0]  # pick an arbitrary secondary snap
      # Lines from first snap point (p==q) to proposed second snap vertices (p2->q2)
      pre_snapped_line = QtCore.QLineF(q, p2)
      post_snapped_line = QtCore.QLineF(q, q2)
      #if pre_snapped_line.length() - post_snapped_line.length() <= self.scene().snapDist:
      theta = pre_snapped_line.angleTo(post_snapped_line)
      #self._log.trace('snap-rotating {} about {} from {} to {}', theta, q, p2, q2)
      scene_xform2 = QtGui.QTransform.fromTranslate(q.x(), q.y()) \
                                     .rotate(-theta) \
                                     .translate(-q.x(), -q.y())
      #self.setTransform(self._base_xform * scene_xform * scene_xform2)
      self.setTransform(self.transform() * scene_xform2)
      return q2

  def snapToShapesByRotationWithALittleNudge(self, q):
    '''Snap (by rotating self.transform() about q) to the nearest other Tile snap point
      (if within snapDist).  Return the snap QPointF.
    '''
    nearSnaps2 = self.nearestSnaps(self.scene().snapDist, excludePt=q)
    if nearSnaps2:
      nearSnaps2.sort(key=_snapKey)
      pq22, p2, q2 = nearSnaps2[0]  # pick an arbitrary secondary snap
      # Lines from first snap point (p==q) to proposed second snap vertices (p2->q2)
      pre_snapped_line = QtCore.QLineF(q, p2)
      post_snapped_line = QtCore.QLineF(q, q2)
      #if pre_snapped_line.length() - post_snapped_line.length() <= self.scene().snapDist:
      theta = pre_snapped_line.angleTo(post_snapped_line)
      #self._log.trace('snap-rotating {} about {} from {} to {}', theta, q, p2, q2)
      scene_xform2 = QtGui.QTransform.fromTranslate(q.x(), q.y()) \
                                     .rotate(-theta) \
                                     .translate(-q.x(), -q.y())
      #self.setTransform(self._base_xform * scene_xform * scene_xform2)
      p2p = scene_xform2.map(p2);
      dp2p = q2-p2p
      self.setTransform(self.transform() * scene_xform2 * QtGui.QTransform.fromTranslate(dp2p.x(), dp2p.y()))
      return q2
                          
  def snapToShapesByScaling(self, q):
    '''Snap (by scaling self.transform() about q) to the nearest other Tile snap point
       (if within snapDist).  Return the snap QPointF.
    '''
    nearSnaps2 = self.nearestSnaps(self.scene().snapDist, excludePt=q)
    if nearSnaps2:
      nearSnaps2.sort(key=_snapKey)
      pq22, p2, q2 = nearSnaps2[0]  # pick an arbitrary secondary snap
      # Lines from first snap point (p==q) to proposed second snap vertices (p2->q2)
      pre_snapped_line = QtCore.QLineF(q, p2)
      post_snapped_line = QtCore.QLineF(q, q2)
      scale_factor = post_snapped_line.length() / pre_snapped_line.length()
      scene_xform2 = QtGui.QTransform.fromTranslate(q.x(), q.y()) \
                                     .scale(scale_factor, scale_factor) \
                                     .translate(-q.x(), -q.y())
      self.setTransform(self.transform() * scene_xform2)
      return q2

  def applyDragXforms(self, invert_snap=False):
    'Apply (but do not commit to) self._drag_xlate, self._drag_rotate, and self._drag_scale, snapping afterwards'
    # I do not entirely understand why these transformations have to be done
    # in this seemingly backwards way.
    scene_xform = QtGui.QTransform.fromTranslate(self._sceneXformCenter.x(), self._sceneXformCenter.y()) \
                                  .scale(self._drag_scale*self._drag_mirror, self._drag_scale) \
                                  .rotate(self._drag_rotate * self._drag_mirror) \
                                  .translate(-self._sceneXformCenter.x() + self._drag_xlate.x() * self._drag_mirror
                                            ,-self._sceneXformCenter.y() + self._drag_xlate.y())
    self.setTransform(self._base_xform * scene_xform)
    if invert_snap != bool(self.scene().snapToTilesEnabled): #property("snapEnabled"):
      if self._drag_type == DRAG_XLATE:
        q = self.snapToShapesByXlation() # Xlate a little more, maybe.  Returns snap point
        if not q is None:
          self.snapToShapesByRotation(q) # Rotate about first snap point.
      elif self._drag_type == DRAG_ROTATE:
        self.snapToShapesByRotationWithALittleNudge(self._sceneXformCenter)  # Rotate a little more, maybe.
      elif self._drag_type == DRAG_SCALE:
        self.snapToShapesByScaling(self._sceneXformCenter)  # Scale a little more, maybe.

  def isSnappingInverted(self, gsMouseEvt):
    return bool(gsMouseEvt.modifiers() & QtCore.Qt.ControlModifier)

  def startDrag(self, gsMouseEvt, drag_type):
    if drag_type == DRAG_NONE: return
    self._drag_timer.start()
    for view in self.scene().views():
      view.setCursor(QtCore.Qt.ClosedHandCursor)
    self.initDragXform()
    self._drag_type = drag_type
    self._drag_start_scenePos = gsMouseEvt.scenePos()  # Remember starting mouse position
    #self._log.trace('_sceneXformCenter = {}', self._sceneXformCenter)
    self._drag_start_scene_vector = QtCore.QLineF(self._sceneXformCenter, self._drag_start_scenePos)

  def updateDrag(self, gsMouseEvt):
    #if QtCore.QLineF(QtCore.QPointF(gsMouseEvt.screenPos()), QtCore.QPointF(gsMouseEvt.buttonDownScreenPos(QtCore.Qt.LeftButton))).length() < QtWidgets.QApplication.startDragDistance(): return
    invert_snap = self.isSnappingInverted(gsMouseEvt)
    if self._drag_type == DRAG_XLATE:
      #return super().mouseMoveEvent(gsMouseEvt)
      self._drag_xlate = gsMouseEvt.scenePos() - self._drag_start_scenePos
      #self._log.trace('{}',self._drag_xlate)
    elif self._drag_type == DRAG_ROTATE:
      move_vector = QtCore.QLineF(self._drag_start_scene_vector.p1(), gsMouseEvt.scenePos())
      self._drag_rotate = move_vector.angleTo(self._drag_start_scene_vector)
      if invert_snap != bool(self.scene().snapToAnglesEnabled):
        angular_resolution = 120
        q = 360.0 / angular_resolution
        self._drag_rotate = q * round(float(self._drag_rotate) / q)
        del q
      del move_vector
    elif self._drag_type == DRAG_SCALE:
      move_vector = QtCore.QLineF(self._drag_start_scene_vector.p1(), gsMouseEvt.scenePos())
      self._drag_scale = move_vector.length() / self._drag_start_scene_vector.length()
      if not invert_snap:
        # TODO: round to integral multiples/fractions of: 1, sqrt(2), phi, sqrt(3), e, pi
        if self._drag_scale >= 1:
          self._drag_scale = round(self._drag_scale)
        else:
          self._drag_scale = 1 / round(1/self._drag_scale)
      del move_vector
    else:
      #self.setTransform( self._drag_xformer.Transform() )
      return
    self.applyDragXforms(invert_snap)
    if False:
      mimedata = QtCore.QMimeData()
      mimedata.setData(MIME_TYPE_SVG, dummySVG)
      drag = QtGui.QDrag(gsMouseEvt.widget())
      drag.setMimeData(mimedata)
      drag.exec_()

  def stopDrag(self, gsMouseEvt):
    self._log.trace('entering')
    if True:
      xforms = self.transformations()
      if xforms              : self._log.warning('{} transformations set!', len(xforms))
      if self.rotation() != 0: self._log.warning('rotation() = {}!', self.rotation())
      if self.scale()    != 1: self._log.warning('scale() = {}!', self.scale())
      self.normalizeTransforms()
    self._log.trace('emitting tileChanged')
    self.scene().tileChanged.emit()
    if self.scene().mouseGrabberItem() is self:
      self.ungrabMouse()
    for view in self.scene().views():
      view.setCursor(QtCore.Qt.ArrowCursor)
    #self._drag_type = DRAG_NONE
    self.initDragXform()

  def cancelDrag(self):
    self._log.trace('entering')
    if self.scene().mouseGrabberItem() is self:
      self.ungrabMouse()
    if self._drag_type != DRAG_NONE:
      self.setTransform(self._base_xform)
      #self._drag_type = DRAG_NONE
      self.initDragXform()
      self._log.debug('drag canceled')
    for view in self.scene().views():
      view.setCursor(QtCore.Qt.ArrowCursor)

  def setSelected(self, selected):
    self._log.trace('selected={}', selected)
    #super().setSelected(selected)
    if not selected and not self.isSelected(): # isSelected() LIES IF PART OF A GROUP
      children = self.childItems()
      self._log.debug('selected={}: deselecting and removing {} children', selected, len(children))
      for it in children:
        assert not it is self
        self.removeFromGroup(it)
        it.setSelected(False) # deselecting children of selcted group doesn't trigger child itemChange!
      self.resetTransforms()
    self._log.trace('selected={}: passing to super()', selected)
    super().setSelected(selected)
    self._log.trace('selected={}: returning', selected)

  def itemChange(self, change, value):
    if change in ( QtWidgets.QGraphicsItem.ItemChildAddedChange
                 , QtWidgets.QGraphicsItem.ItemChildRemovedChange ):
      self._log.trace('{}:{}:clearing shape cache', change,value)
      self.flushShape()
      if change == QtWidgets.QGraphicsItem.ItemChildRemovedChange and not len(self.childItems()):
        self._log.trace('no children left')
        self.resetTransforms()
      self.computeSceneXformCenter()
    if change == QtWidgets.QGraphicsItem.ItemSelectedHasChanged:
      if not value:
        assert not self.isSelected()
        self.flushShape()
        children = self.childItems()
        self._log.debug('ItemSelectedHasChanged:{}:deselecting and removing {} children', value, len(children))
        for it in children:
          #self.removeFromGroup(it) # segfault
          it.setSelected(False) # deselecting children of selcted group doesn't trigger child itemChange!
      else: self._log.trace('ItemSelectedHasChanged:{}',value)
    return super().itemChange(change, value)

  def mousePressEvent(self, gsMouseEvt):
    if not self.isSelected():
      self.setSelected(True)
    if not (gsMouseEvt.modifiers() & QtCore.Qt.ShiftModifier):
      if self._drag_type is DRAG_NONE:
        drag_type = mapDragButton(gsMouseEvt.button())
        self.startDrag(gsMouseEvt, drag_type)
      else:
        self.stopDrag(gsMouseEvt)
    gsMouseEvt.accept()

  def mouseMoveEvent(self, gsMouseEvt):
    self.updateDrag(gsMouseEvt)
    gsMouseEvt.accept()

  def mouseReleaseEvent(self, gsMouseEvt):
    if self._drag_type != DRAG_NONE and not self._drag_timer.hasExpired(200):
      # normal/brief click: pick up, keep dragging until another click, reduce mouse button finger strain.
      #self.setAcceptHoverEvents(True)
      self.grabMouse() # qgraphicsview must have mouseTracking enabled
      gsMouseEvt.accept()
    else:
      if self._drag_type != DRAG_NONE:
        self.stopDrag(gsMouseEvt)
        #self.setAcceptHoverEvents(False)
      if self.scene().mouseGrabberItem() is self:
        self.ungrabMouse()
      gsMouseEvt.accept()
      #return super().mouseReleaseEvent(gsMouseEvt)

  def keyPressEvent(self, keyEvt):
    # keyEvt.isAccepted() is True by default
    k = keyEvt.key()
    self._log.debug('key={}, nativeVirtualKey={}', k, keyEvt.nativeVirtualKey())
    if k == QtCore.Qt.Key_Escape and self._drag_type != DRAG_NONE:
      self.cancelDrag()
      if self.scene().mouseGrabberItem() is self:
        self.ungrabMouse()
    elif k == QtCore.Qt.Key_BracketLeft  or k == QtCore.Qt.Key_Slash: 
      self._drag_rotate -= 15
      self.applyDragXforms()
    elif k == QtCore.Qt.Key_BracketRight or k == QtCore.Qt.Key_Asterisk:
      self._drag_rotate += 15
      self.applyDragXforms()
    elif k >= QtCore.Qt.Key_0 and k <= QtCore.Qt.Key_9:
      i = k - QtCore.Qt.Key_0
      if i == 0: i = 10
      if keyEvt.modifiers() & QtCore.Qt.AltModifier:
        self._drag_scale = 1.0/i
      else:
        self._drag_scale = float(i)
      self.applyDragXforms()
    else: return super().keyPressEvent(keyEvt) # QGraphicsItem calls keyEvt.ignore()

  def paint(self, painter, option, widget=0):
    # Don't draw default bounding rectangle
    # (Children independently draw themselves)
    # Any painting here ends up behind all children.
    if self._log.isEnabledFor('debug'):
      ctr = self.mapFromScene(self._sceneXformCenter)
      if len(self.childItems()):
        painter.setPen(QtGui.QPen(QtCore.Qt.blue, 0))
        painter.drawRect(self.boundingRect())
        painter.drawEllipse(ctr, 1, 1)
        # Draw crosshairs through center
        painter.drawLine(ctr+QtCore.QPointF(-1,0), ctr+QtCore.QPointF(1,0))
        painter.drawLine(ctr+QtCore.QPointF(0,-1), ctr+QtCore.QPointF(0,1))
      if self._nearSnapsDebug is None or len(self._nearSnapsDebug)==0:
        painter.setPen(QtGui.QPen(QtCore.Qt.yellow, 0))
        painter.drawEllipse(ctr, .25, .25)
      else:
        for snapTup in self._nearSnapsDebug:
          painter.setPen(QtGui.QPen(QtCore.Qt.magenta, 0))
          p = self.mapFromScene(snapTup[1])
          painter.drawEllipse(p, .25, .25)
          painter.setPen(QtGui.QPen(QtCore.Qt.red, 0))
          q = self.mapFromScene(snapTup[2])
          painter.drawEllipse(p, .25, .25)

if __name__=='__main__': unittest.main()

