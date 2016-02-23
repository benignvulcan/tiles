#!/usr/bin/env python3

import re
import xml.etree.ElementTree as ET
from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QPolygonF, QTransform

logger = None

def ParseColor(s):
  c = None
  if re.match(r'^\s*#[0-9A-Fa-f]{3}\s*$', s):
    c = (int(h+h,16) for h in s[1:])
  elif re.match(r'^\s*#[0-9A-Fa-f]{6}\s*$', s):
    c = (int(h,16) for h in [s[1:3],s[3:5],s[5:7]])
  return c

def SplitFloatValues(s):
  if not s or s.isspace(): return []
  return [float(n) for n in re.split(r'\s+,?\s*|,\s*', s.strip())]

def FloatsToQPointFs(values):
  return map(lambda xy: QPointF(*xy), zip(values[::2], values[1::2]))

def ParseTransformAttrib(s):
  # where s is an SVG transform attribute such as "translate(-2,1) matrix(0 1 2 3 4 5)"
  # return a list of QTransforms
  xforms = []
  s = s.lower()
  while s:
    s = re.sub(r'^\s+,?\s+', '', s)  # remove leading WS,WS
    m = re.match(r'\s*(\w+)\s*\(((\s*[0-9e.+-]+\s*,?)+)\)', s) # match identifier(numbers) clause
    if m:
      values = SplitFloatValues(m.group(2))
      if m.group(1) == 'translate':
        if len(values) == 1: values.append(0)
        xforms.append( QTransform.fromTranslate(*values) )
      elif m.group(1) == 'scale':
        if len(values) == 1: values.append(values[0])
        xforms.append( QTransform.fromScale(*values) )
      elif m.group(1) == 'rotate':
        xforms.append( QTransform().rotate(values[0]) )  # TODO: handle cx,cy values
      elif m.group(1) == 'matrix':
        logger.trace('matrix({}): m.group(2) = {}', values, m.group(2))
        xforms.append( QTransform( values[0], values[1], 0
                                 , values[2], values[3], 0
                                 , values[4], values[5], 1) )
      # TODO: handle skewX and skewY
      else: logger.warning('unrecognized transform: {}', m.group())
      s = s[m.end()+1:]
    else:
      if s: logger.warning('unparsed transform: {}', s)
      break
  return xforms

def ParseSvgPathData(s):
  pathCmds = []
  s = s.strip()
  while s:
    m = re.match(r'\s*([A-Za-z])((\s*[0-9e.+-]*\s*,?)+)', s) # match "C numbers" clause
    if m:
      values = SplitFloatValues(m.group(2))
      pathCmds.append( (m.group(1), values) )
      s = s[m.end():]
    else:
      if s: logger.warning('unparsed path data: {}', s)
      break
  return pathCmds

def SvgPathCmdsToPolygons(pathCmds):
  logger.trace('{}', pathCmds)
  polygons = []
  points = []
  #pos = QPointF(0,0)
  for (cmd, args) in pathCmds:
    if cmd in 'MmLl':
      coords = FloatsToQPointFs(args)
    if cmd in 'Mm' and points:
      polygons.append.QPolygonF(points)
      points = coords
    elif cmd in 'MmLl':
      points.extend(coords)
    elif cmd in 'Zz':
      polygons.append(QPolygonF(points))
      points = []
    else:
      logger.trace('ignoring path data of type "{}"', cmd)
  return polygons

def ParseSvgAttribs(e):
  d = {}
  for k,v in e.attrib.items():
    if k in 'tiles:shapeno'.split():
      d[k] = int(v)
    elif k in 'tiles:size cx cy rx ry'.split():
      d[k] = float(v)
    elif k == 'points':
      values = SplitFloatValues(v)
      points = FloatsToQPointFs(values)
      logger.trace('polygon {}', points)
      d[k] = points
    elif k == 'd':
      d[k] = ParseSvgPathData(v)
    elif k == 'fill':
      c = ParseColor(v)
      if c:
        d[k] = c
      else: logger.trace('unparsed attribute: {}="{}"', k, v)
    elif k == 'transform':
      xform = QTransform()
      for t in reversed(ParseTransformAttrib(v)):
        xform *= t
      d[k] = xform
    else: logger.trace('unparsed attribute: {}="{}"', k, v)
  return d

