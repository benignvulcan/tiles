#!/usr/bin/env python3

import math, unittest
#from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QPointF, QLineF
from PyQt5.QtGui import QPolygonF

class QMathTurtle(object):
  '''A MathTurtle accumulates vectors via the usual Turtle methods.
     Angles are in radians unless otherwise specified.
     Starts by default at (0,0) heading 0 (+x)
  '''
  # This class should accept other QMathTurtles as points.

  def __init__(self, pos=None, degreesHeading=None, radiansHeading=None):
    self.reset(pos, degreesHeading, radiansHeading)

  def reset(self, pos=None, degreesHeading=None, radiansHeading=None):
    if isinstance(pos, QMathTurtle):
      assert degreesHeading is None and radiansHeading is None
      pos = pos.pos()
      heading = pos.radiansHeading()
    else:
      if pos is None:
        pos = QPointF(0,0)
      assert degreesHeading is None or radiansHeading is None
      if not degreesHeading is None:
        heading = math.radians(degreesHeading)
      elif not radiansHeading is None:
        heading = radiansHeading
      else:
        heading = 0
    self._pos = pos
    self._heading = heading
    return self

  def home(self):
    self.goto(QPointF(0,0))

  def pos(self):
    return self._pos

  def radiansHeading(self, heading=None):
    'Set the absolute heading, in radians.  If passed a QMathTurtle, copy its heading.'
    if heading is None:
      return self._heading
    elif isinstance(heading, QMathTurtle):
      self._heading = heading.radiansHeading()
    else:
      self._heading = heading

  def degreesHeading(self, heading=None):
    if heading is None:
      return math.degrees(self._heading)
    elif isinstance(heading, QMathTurtle):
      self._heading = heading.radiansHeading()
    else:
      self._heading = math.radians(heading) % (2*math.pi)

  def ltr(self, theta):
    'Turn left theta radians'
    self._heading = math.fmod(self._heading + theta, 2*math.pi)
    return self
  def leftRadians(theta): return self.ltr(theta)

  def lt(self, theta):
    'Turn left theta degrees'
    return self.ltr(math.radians(theta))
  def left(self, theta): return self.lt(theta)

  def rtr(self, theta):
    'Turn right theta radians'
    self._heading = math.fmod(self._heading - theta, 2*math.pi)
    return self
  def rightRadians(theta): return self.rtr(theta)

  def rt(self, theta):
    'Turn right theta degrees'
    return self.rtr(math.radians(theta))
  def right(self, theta): return self.rt(theta)

  def fd(self, r):
    dx = r * math.cos(self._heading)
    dy = r * math.sin(self._heading)
    return self.goto(self._pos + QPointF(dx,dy))
  def forward(self, r): return self.fd(r)

  def bk(self, r):
    return self.forward(-r)
  def back(self, r): return self.back(r)

  def goto_offset(self, offset):
    return self.goto(self._pos + offset)

  def goto(self, pos):
    if isinstance(pos, QMathTurtle):
      pos = pos.pos()
    self._pos = pos
    return self

  def distance_to(self, point):
    'Compute distance to the given point.'
    if isinstance(point, QMathTurtle): point = point.pos()
    delta = point - self._pos
    return math.sqrt( delta.x()**2 + delta.y()**2 )

  def abs_radians_to(self, point):
    'Return absolute angle to the given point.'
    if isinstance(point, QMathTurtle):
      point = point.pos()
    delta = point - self._pos
    theta = math.atan2(delta.y(), delta.x())
    return theta
  def abs_degrees_to(self, point):
    return math.degrees(self.abs_radians_to(point))

  def radians_to(self, point):
    'Return relative angle to the given point, in the domain (-pi, +pi]'
    theta = self.abs_radians_to(point) - self._heading
    if theta > math.pi: theta -= math.pi*2
    elif theta <= -math.pi: theta += math.pi*2
    return theta
  def degrees_to(self, point):
    return math.degrees(self.radians_to(point))

  def turn_towards(self, point):
    'Change heading to face towards the given point.'
    return self.ltr(self.radians_to(point))

class RecordingTurtle(QMathTurtle):
  '''In addition to accumulating vectors, provide pen up/down methods
     and record all drawn polygons.'''

  def reset(self, pos=None, heading=None, angleConversion=None):
    super().reset(pos,heading, angleConversion)
    self._polygons = []
    self._vertices = [self._pos]
    self._pendown = 1

  def pu(self):
    '''Pen-up commands stack, so that every pen-up requires a corresponding
       pen-down.  Only when each pen-up has been undone by a pen-down will
       movements actually be recorded.  This way, any turtle procedure can
       be executed without recording, even if it uses (matching) pen-up and
       pen-down methods itself.'''
    self._pendown -= 1
    if len(self._vertices) > 1:
      self._polygons.append(QPolygonF(self._vertices))
      self._vertices = []
    return self
  def penup(self): return self.pu()

  def pd(self):
    '''Pen-down commands undo pen-up commands, but do not themselves stack.'''
    self._pendown += 1
    if self._pendown > 1: self._pendown = 1
    self._vertices = [self._pos]
    return self
  def pendown(self): return self.pd()

  def goto(self, pos):
    super().goto(pos)
    if self._pendown > 0:
      self._vertices.append(pos)
    return self

  def vertices(self):
    'Return vertices of currently drawn polygon'
    return self._vertices[:]

  def polygon(self):
    'Return currently drawn polygon'
    # Note that while this won't be just 1 point, it could be just 1 line.
    return QPolygonF(self._vertices)

  def polygons(self):
    'Return all polygons drawn'
    polys = self._polygons[:]
    if self._vertices:
      polys.append(QPolygonF(self._vertices))
    return polys

#if hasattr(math, 'isclose'):
#  _isclose = math.isclose
#else:
#  # from Python 3.5:
#  def _isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
#    return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

class TestQMathTurtle(unittest.TestCase):
  def assertAlmostEqualPt(self, p, q):
    self.assertAlmostEqual(p.x(), q.x())
    self.assertAlmostEqual(p.y(), q.y())
  def test_simple_turtle(self):
    t = QMathTurtle()
    self.assertIsInstance(t, QMathTurtle)
    self.assertEqual(t.pos(), QPointF(0,0))
    self.assertEqual(t.degreesHeading(), 0)
    self.assertEqual(t.radiansHeading(), 0)
    self.assertIs(t.lt(45), t)
    self.assertAlmostEqual(t.degreesHeading(), 45)
    self.assertIs(t.fd(10000), t)
    self.assertAlmostEqual(t.degreesHeading(), 45)
    self.assertAlmostEqualPt(t.pos(), QPointF(7071.06781187, 7071.06781187))
    self.assertIs(t.bk(10000), t)
    self.assertIs(t.rt(45), t)
    self.assertAlmostEqual(t.degreesHeading(), 0)
    self.assertAlmostEqualPt(t.pos(), QPointF(0,0))
    t.lt(30).fd(100)
    self.assertAlmostEqual( t.abs_degrees_to(QPointF(0,0)), -150 )
    self.assertAlmostEqual( t.abs_degrees_to(t), 0 )
    self.assertAlmostEqual( t.radians_to(QPointF(0,0)), math.pi)
    self.assertAlmostEqual( t.degrees_to(QPointF(0,0)), 180 )
    self.assertAlmostEqual( t.distance_to(QPointF(0,0)), 100 )
    self.assertAlmostEqual( t.distance_to(t), 0 )
    self.assertIs(t.turn_towards(QPointF(0,0)), t)
    self.assertAlmostEqual( t.degreesHeading(), 210 )
    t.reset()
    self.assertAlmostEqual(t.degreesHeading(), 0)
    self.assertAlmostEqualPt(t.pos(), QPointF(0,0))
    for i in range(9):
      self.assertIs(t, t.fd(10))
      self.assertIs(t, t.lt(60))
    self.assertAlmostEqual(t.degreesHeading(), 180)

class TestRecordingTurtle(TestQMathTurtle):
  def test_simple_recording(self):
    t = RecordingTurtle()
    self.assertIsInstance(t, RecordingTurtle)
    self.assertIsInstance(t, QMathTurtle)
    for i in range(4): t.fd(10).rt(90)
    vs = t.vertices()
    map(self.assertAlmostEqualPt, zip(vs, [QPointF(0,0),QPointF(10,0),QPointF(10,10),QPointF(0,10),QPointF(0,0)]))

if __name__=='__main__': unittest.main()
