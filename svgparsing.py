#!/usr/bin/env python3

import re
import itertools
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
  'Convert an iterable of floats into a list of QPointF objects (two floats per point)'
  return list( QPointF(*xy) for xy in zip(values[::2], values[1::2]) )

def ParseTransformAttrib(s):
  # where s is an SVG transform attribute such as "translate(-2,1) matrix(0 1 2 3 4 5)"
  # return a list of QTransforms
  xforms = []
  s = s.lower()
  while s:
    s = re.sub(r'^\s+,?\s+', '', s)  # remove leading WS,WS
    m = re.match(r'\s*(\w+)\s*\(((\s*[0-9Ee.+-]+\s*,?)+)\)', s) # match identifier(numbers) clause
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
  '''Break SVG path data (the value of a 'd' attrib) down into a list of strings,
    each containing a command with its arguments.
  '''
  pathCmds = []
  s = s.strip()
  while s:
    # Commands are a single letter. Whitespace is only required for separating numbers.
    m = re.match(r'\s*([A-Za-z])((\s*[0-9Ee.+-]*\s*,?)+)', s) # match "C numbers" clause
    if m:
      values = SplitFloatValues(m.group(2))
      pathCmds.append( (m.group(1), values) )
      s = s[m.end():]
    else:
      if s: logger.warning('unparsed path data: {}', s)
      break
  return pathCmds

def SvgPathCmdsToPolygons(pathCmds):
  '''Parse a list of SVG path command strings into a list of QPolygonF objects.

  pathCmds = a list of strings where each string starts with an SVG path command character
             and is followed by a list of numbers.
             The list of numbers are x,y coordinate pairs.

  Lowercase commands use coordinates relative "to the start of the command".
  Commands with multiple sets of arguments are considered separate commands!
  Which just means every coordinate is relative to the previous, not to the first.

  SVG path commands are:
    M,m  new subpath starting with given coords
    L,l  lines from current point to given coords
    H,h  horizontal lines to given X ordinate(s)
    V,v  vertical lines to given Y ordinate(s)
    C,c  cubic bezier curve from current point with given control points
    S,s  "shorthand/smooth" cubic bezier curve from current point with given control points
    Z,z  close subpath
  '''
  # Note that PolygonTileItem() currently ignores all but the first polygon in a path.
  logger.trace('{}', pathCmds)

  polygons = []       # accumulated list of QPolygonF objects (SVG subpaths)
  points = []         # accumulated list of QPointF objects (absolute coordinates)
  pos = None          # current point (absolute coordinates)

  def next_poly():
    'Start a new subpath.'
    if points:
      polygons.append(QPolygonF(points))
      points.clear()

  for (cmd, args) in pathCmds:

    if cmd in 'MmLl':
      # Most commands are followed by a list of numbers that need parsing
      coords = FloatsToQPointFs(args)
      if not coords:
        logger.trace('move/line-to cmd has no coords', cmd)
        continue

    if cmd == 'M':
      next_poly()
      points = coords
      pos = points[-1]
    elif cmd == 'm':
      next_poly()
      if pos is None:
        points = list(itertools.accumulate(coords))
      else:
        points = list(itertools.accumulate([pos]+coords))[1:]
      pos = points[-1]
    elif cmd == 'L':
      points.extend(coords)
      pos = points[-1]
    elif cmd == 'l':
      if pos is None:
        logger.trace('no current pos for "l" cmd')
      else:
        points.extend(list(itertools.accumulate([pos]+coords))[1:])
        pos = points[-1]
    elif cmd in 'Zz':
      # SVG Z cmd connects current pos to start pos, but this is not needed for Tiles.
      next_poly()
    else:
      logger.trace('ignoring path data of type "{}"', cmd)

  next_poly()
  return polygons

def ParseStyleAttrib(s):
  # I would love to use someone else's CSS parser.
  # Good luck figuring out which to trust and determining/satisfying its dependencies.
  d = {}
  decls = s.split(';')
  for decl in decls:
    namevalue = decl.split(':')
    if len(namevalue) == 2:
      d[namevalue[0].strip()] = namevalue[1].strip()
  return d

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
    elif k == 'style':
      ds = ParseStyleAttrib(v)
      ignored = []
      for name in ds:
        if name == 'fill':
          d['fill'] = ParseColor(ds['fill'])
        else:
          ignored.append(name)
      if ignored:
        logger.trace('ignoring style declarations for: {}.', ','.join(ignored))
    else: logger.trace('unparsed attribute: {}="{}"', k, v)
  return d

