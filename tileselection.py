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

class TestQPointF(unittest.TestCase):
  def test_QPointF(self):
    p = QtCore.QPointF(2.0, 3.0)
    q = QtCore.QPointF(5.0, 7.0)
    self.assertIsNot(p,q)
    qp = q - p
    self.assertIsNot(p,q)
    self.assertIsNot(qp, q)
    self.assertIsNot(qp, p)

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
  'Return a list of QPointF, the positions of the elements of the given QPainterPath.'
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
  'Return the drag mode corresponding to the given mouse button.'
  if   button == QtCore.Qt.LeftButton  : return DRAG_XLATE
  elif button == QtCore.Qt.RightButton : return DRAG_ROTATE
  elif button == QtCore.Qt.MiddleButton: return DRAG_SCALE
  else: return DRAG_NONE

'''
  QKeyEvent.key() provides no clue about shifted digit keys.
  QKeyEvent.nativeVirtualKey() provides no clue about shifted digit keys.
  QKeyEvent.nativeScanCode() flat doesn't work on a Mac.
  Fuck knows how to do this in a language/keyboard independent fashion.
  Are there really millions of keyboards in some country that don't do shifted digits?
  Probably should use Alt instead of shift.
'''
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

def _snapKey(s):
  'Return the sort key for the given snap tuple.'
  return ( s[1].x(),s[1].y(), s[2].x(),s[2].y() )

class SelectionGroup(QtWidgets.QGraphicsItemGroup):
  '''A selection of TileItems that is being transformed.
    In this application, all selected Tiles are added to this SelectionGroup,
    and all unselected Tiles are not.  This SelectionGroup is always
    "selected", even if it has no items in it.
  '''

  def __init__(self, logger, parent=None):
    self._shape = None  # a cached QPainterPath that is the union of all selected Tiles, for collision/hit-testing
    self._log = logger
    super().__init__(parent=parent)
    self.setFlags( self.flags()
                 | QtWidgets.QGraphicsItem.ItemIsFocusable
                 | QtWidgets.QGraphicsItem.ItemIsSelectable
                 | QtWidgets.QGraphicsItem.ItemIsMovable
                 | QtWidgets.QGraphicsItem.ItemSendsGeometryChanges
                 )
    self._drag_timer = QtCore.QElapsedTimer()
    self._nearSnapsDebug = None
    self.initDragXform()

  def initDragXform(self):
    '''(Re)initialize the various transforms that can be done by dragging or keyboard shortcuts.
      Qt's built-in transforms change the mapping of this item onto the scene.
      Children have their own local coordinates,
        and their own transforms mapping them to their parent's coordiantes.
      Painting is always done in local coordinates.
    '''
    self._drag_type = DRAG_NONE
    # Transforms done about the starting drag point:
    self._drag_xlate = QtCore.QPointF()
    self._drag_rotate = 0
    self._drag_scale = 1
    self._drag_mirror = 1
    # Transforms done about the current center:
    self._kbd_rotate = 0
    self._kbd_scale = 1
    # Remember the center of drag transforms in scene coordinates
    # so it doesn't move while dragging.
    self._dragXformCenter = self.sceneBoundingRect().center()

  def editColor(self):
    n = 0
    firstColor = None
    heterogeneous = False
    (r,g,b,a) = (0,0,0,0)
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
      a += c.alpha()
      n += 1
    if n:
      r = float(r)/n
      g = float(g)/n
      b = float(b)/n
      a = float(a)/n
      c = QtGui.QColor(r,g,b,a)
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
    'Return a QPainterPath (in Item coordinates) for collision/hit testing.'
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
    'A Tile is being added or removed, so forget the cached shape union.'
    self.prepareGeometryChange()
    self._shape = None

  def resetTransforms(self):
    '''Reset the transformations of this SelectionGroup.
       Be sure to call this when clearing the selection.
    '''
    self._log.trace('{} children', len(self.childItems()))
    self.resetTransform()
    self.setPos(0,0)
    self.flushShape()
    self._log.trace('returning')

  def normalizeTransforms(self):
    '''Reset the transformations of this SelectionGroup (to identity)
       while retaining the effect they had on the children.
       This effectively propagates the group transforms to each child.
       Used to apply/finalize a drag transformation.
    '''
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
    'Reset the transform of each contained/selected shape.'
    # Qt BUG (sort of):
    #   QGraphicsItemGroup caches bounding rectangle and only updates
    #     it during addToGroup() and removeFromGroup() !
    #  Compensate by removing and re-adding each child after resetting.
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

  def rotateBy(self, deg):
    self._kbd_rotate -= deg
    self.applyDragXforms()
    if self._drag_type is DRAG_NONE:
      self.normalizeTransforms()
      self.initDragXform()

  def scaleBy(self, factor):
    self._kbd_scale *= factor
    self.applyDragXforms()
    if self._drag_type is DRAG_NONE:
      self.normalizeTransforms()
      self.initDragXform()

  def mirror(self):
    'Flip this selection horizontally about the center.'
    self._drag_mirror = -self._drag_mirror
    self.applyDragXforms()
    if self._drag_type is DRAG_NONE:
      self.normalizeTransforms()
      self.initDragXform()
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

    # Before looping through all child items, first check if any snapping is possible at all.
    snap_search_rect = self.sceneBoundingRect().marginsAdded(snap_margins)
    nearby_items = self.scene().items(snap_search_rect)
    nearby_tiles = [it for it in nearby_items if not it.isSelected() and hasattr(it, "sceneSnapPoints")]
    if not nearby_tiles:
      return []

    # It's distinctly faster to let QGraphicsScene compare each child tile with
    # other tiles than to ask it to compare all child points with other tiles,
    # though this still ends up O(n*n) when dragging many tiles over many tiles.
    for child in self.childItems():
      snap_search_rect = child.sceneBoundingRect().marginsAdded(snap_margins)
      nearby_items = self.scene().items(snap_search_rect)
      nearby_tiles = [it for it in nearby_items if not it.isSelected() and hasattr(it, "sceneSnapPoints")]
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

  def snapByXlation(self, originPt, p, q):
    '''Translate such that p aligns with q.'''
    snapDelta = q - p  # if target q is greater, snapDelta from p will be positive
    return QtGui.QTransform.fromTranslate(snapDelta.x()*self._drag_mirror, snapDelta.y())

  def snapByRotation(self, originPt, p, q):
    '''Rotate about originPt such that p aligns with q.'''
    # Construct lines from the center of rotation to
    #   * the snap point p on one of the tiles in this selection
    #   * and q on some other (unselected) tile.
    pre_snapped_line = QtCore.QLineF(originPt, p)
    post_snapped_line = QtCore.QLineF(originPt, q)
    theta = pre_snapped_line.angleTo(post_snapped_line)
    return QtGui.QTransform.fromTranslate(originPt.x(), originPt.y()) \
                           .rotate(-theta) \
                           .translate(-originPt.x(), -originPt.y())

  def snapByRotationWithRadialNudge(self, originPt, p, q):
    '''Rotate about originPt such that p is in line with q (and originPt),
       then translate radially so they align.
    '''
    rotation_xform = self.snapByRotation(originPt, p, q) # first compute simple rotation snap
    p2 = rotation_xform.map(p)     # then ask where that moves point p to
    nudge_offset = q - p2
    return rotation_xform * QtGui.QTransform.fromTranslate(nudge_offset.x(), nudge_offset.y())

  def snapByScaling(self, originPt, p, q):
    '''Scale about originPt such that p aligns with q.'''
    # Construct lines from the center of scaling to
    #   * the snap point p on one of the tiles in this selection
    #   * and q on some other (unselected) tile.
    pre_snapped_line = QtCore.QLineF(originPt, p)
    post_snapped_line = QtCore.QLineF(originPt, q)
    scale_factor = post_snapped_line.length() / pre_snapped_line.length()
    return QtGui.QTransform.fromTranslate(originPt.x(), originPt.y()) \
                           .scale(scale_factor, scale_factor) \
                           .translate(-originPt.x(), -originPt.y())

  def snapToTiles(self, snap_fn, originPt=None):
    '''Snap (by using snap_fn to transform about originPt)
       to the nearest other Tile snap point (if within snapDist).
       Return the other QPointF or None.
    '''
    nearSnaps = self.nearestSnaps(self.scene().snapDist, excludePt=originPt)
    if nearSnaps:
      nearSnaps.sort(key=_snapKey)
      _dist_squared, selfPt, otherPt = nearSnaps[0]  # pick an arbitrary secondary snap
      snap_xform = snap_fn(originPt, selfPt, otherPt)
      self.setTransform(self.transform() * snap_xform)
      return otherPt  # the point this shape was transformed to concide with

  def applyDragXforms(self, invert_snap=False):
    'Apply (but do not commit to) self._drag_xlate, self._drag_rotate, and self._drag_scale, snapping afterwards'
    drag_xforms = (QtGui.QTransform()
                     .translate(self._dragXformCenter.x(), self._dragXformCenter.y())
                     .scale(self._drag_scale*self._drag_mirror, self._drag_scale)
                     .rotate(self._drag_rotate * self._drag_mirror)
                     .translate(-self._dragXformCenter.x() + self._drag_xlate.x() * self._drag_mirror
                               ,-self._dragXformCenter.y() + self._drag_xlate.y())
                  )
    self.setTransform(drag_xforms)
    current_ctr = self.sceneBoundingRect().center()
    kbd_xforms = (QtGui.QTransform()
                    .translate(current_ctr.x(), current_ctr.y())
                    .scale(self._kbd_scale, self._kbd_scale)
                    .rotate(self._kbd_rotate)
                    .translate(-current_ctr.x(), -current_ctr.y())
                 )
    self.setTransform(drag_xforms * kbd_xforms)
    if invert_snap != bool(self.scene().snapToTilesEnabled): #property("snapEnabled"):
      if self._drag_type == DRAG_XLATE:
        # Xlate a little more, maybe.  Returns snap point
        q = self.snapToTiles(self.snapByXlation, None)
        if not q is None:
          # Rotate about first snap point, maybe.
          self.snapToTiles(self.snapByRotation, q)
      elif self._drag_type == DRAG_ROTATE:
        # Rotate a little more, maybe.
        self.snapToTiles(self.snapByRotationWithRadialNudge, self._dragXformCenter)
      elif self._drag_type == DRAG_SCALE:
        # Scale a little more, maybe.
        self.snapToTiles(self.snapByScaling, self._dragXformCenter)
        # TODO: scale about the first snap to match a second

  def isSnappingInverted(self, gsMouseEvt):
    'Return True if the user was holding down the snap-modifier key.'
    return bool(gsMouseEvt.modifiers() & QtCore.Qt.ControlModifier)

  def startDrag(self, gsMouseEvt, drag_type):
    'Initialize and remember the beginning of a drag operation'
    if drag_type == DRAG_NONE: return
    self._drag_timer.start()
    for view in self.scene().views():
      view.setCursor(QtCore.Qt.ClosedHandCursor)
    self.initDragXform()
    self._drag_type = drag_type
    self._drag_start_scenePos = gsMouseEvt.scenePos()  # Remember starting mouse position
    self._drag_start_scene_vector = QtCore.QLineF(self._dragXformCenter, self._drag_start_scenePos)

  def updateDrag(self, gsMouseEvt):
    'Modify the current drag transformation, given a mouse movement.'
    invert_snap = self.isSnappingInverted(gsMouseEvt)
    if self._drag_type == DRAG_XLATE:
      self._drag_xlate = gsMouseEvt.scenePos() - self._drag_start_scenePos
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
    '''Finish the current drag transformation, keeping the dragged transforms.
    '''
    self._log.trace('entering')
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
    self.initDragXform()

  def cancelDrag(self):
    '''Abandon the current drag transformation,
       reverting to the transforms in effect when the drag started.
    '''
    self._log.trace('entering')
    if self.scene().mouseGrabberItem() is self:
      self.ungrabMouse()
    if self._drag_type != DRAG_NONE:
      self.resetTransforms()
      self.initDragXform()
      self._log.debug('drag canceled')
    for view in self.scene().views():
      view.setCursor(QtCore.Qt.ArrowCursor)

  def itemChange(self, change, value):
    'Some aspect of this SelectionGroup has changed. Adjust accordingly.'
    if change in ( QtWidgets.QGraphicsItem.ItemChildAddedChange
                 , QtWidgets.QGraphicsItem.ItemChildRemovedChange ):
      self._log.trace('{}:{}:clearing shape cache', change,value)
      self.flushShape()
      if change == QtWidgets.QGraphicsItem.ItemChildRemovedChange and not len(self.childItems()):
        self._log.trace('no children left')
        self.resetTransforms()
    else:
      self._log.trace('ItemSelectedHasChanged:{}',value)
    return super().itemChange(change, value)

  def mousePressEvent(self, gsMouseEvt):
    '''The user clicked on a tile that either:
       * was not selected:
         - and just became the only tile in the selection and should be ready to now drag
         - or was just added to the existing selection (using the modifer key)
             and should not be dragged
       * was already selected:
         - and should now be dragged
         - or should now be de-selected if clicking with the modifier
    '''
    shiftmod = (gsMouseEvt.modifiers() & QtCore.Qt.ShiftModifier)
    if shiftmod:
      # Un-select a currently selected individual tile
      mpos = gsMouseEvt.scenePos()
      for it in reversed(self.childItems()):
        if it.contains(it.mapFromScene(mpos)):
          it.setSelected(False)
          break
    else:
      # Start or stop a drag.
      if self._drag_type is DRAG_NONE:
        drag_type = mapDragButton(gsMouseEvt.button())
        self.startDrag(gsMouseEvt, drag_type)
      else:
        self.stopDrag(gsMouseEvt)
    gsMouseEvt.accept()

  def mouseMoveEvent(self, gsMouseEvt):
    'The mouse moved (while this object has captured mouse events).'
    self.updateDrag(gsMouseEvt)
    gsMouseEvt.accept()

  def mouseReleaseEvent(self, gsMouseEvt):
    '''The user let go of a mouse button.
       If it was the end of a plain single click, keep dragging.
       If the button had been down for a while, stop dragging now.
    '''
    if self._drag_type != DRAG_NONE and not self._drag_timer.hasExpired(200):  # 200 ms = 1/5 sec
      '''This was a normal/brief click:
         Keep hold of the tile / keep dragging, until another click, to reduce mouse button finger strain.
      '''
      self.grabMouse() # qgraphicsview must have mouseTracking enabled
      gsMouseEvt.accept()
    else:
      if self._drag_type != DRAG_NONE:
        self.stopDrag(gsMouseEvt)
      if self.scene().mouseGrabberItem() is self:
        self.ungrabMouse()
      gsMouseEvt.accept()

  def keyPressEvent(self, keyEvt):
    'While this SelectionGroup is in focus, interpret a keypress.'
    # keyEvt.isAccepted() is True by default
    k = keyEvt.key()
    self._log.debug('key={}, nativeVirtualKey={}', k, keyEvt.nativeVirtualKey())
    if k == QtCore.Qt.Key_Escape and self._drag_type != DRAG_NONE:
      self.cancelDrag()
      if self.scene().mouseGrabberItem() is self:
        self.ungrabMouse()
    elif k == QtCore.Qt.Key_BracketLeft  or k == QtCore.Qt.Key_Slash: 
      self.rotateBy(15)
    elif k == QtCore.Qt.Key_BracketRight or k == QtCore.Qt.Key_Asterisk:
      self.rotateBy(-15)
    elif k >= QtCore.Qt.Key_0 and k <= QtCore.Qt.Key_9:
      i = k - QtCore.Qt.Key_0
      if i == 0: i = 10
      if keyEvt.modifiers() & QtCore.Qt.AltModifier:
        f = 1.0/i
      else:
        f = float(i)
      self.scaleBy(f)
    else: return super().keyPressEvent(keyEvt) # QGraphicsItem calls keyEvt.ignore()

  def paint(self, painter, option, widget=0):
    '''Paint this SelectionGroup object.
         (Prevent default bounding rectangle from being painted.)
       It is normally invisible (you see the child Tiles though).
    '''
    # (Children independently draw themselves)
    # Any painting here ends up behind all children.
    if self._log.isEnabledFor('debug'):
      ctr = self.mapFromScene(self._dragXformCenter)
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

