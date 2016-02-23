
from PyQt5 import QtCore, QtGui

def FormatQPointFs(qpflist):
  return ','.join( '({:.3f},{:.3f})'.format(p.x(),p.y()) for p in qpflist )

PainterPathElementNames = \
  { QtGui.QPainterPath.MoveToElement      : 'M'
  , QtGui.QPainterPath.LineToElement      : 'L'
  , QtGui.QPainterPath.CurveToElement     : 'C'
  , QtGui.QPainterPath.CurveToDataElement : 'D'
  }

def FormatQPainterPath(path):
  en = path.elementCount()
  es = []
  for i in range(en):
    e = path.elementAt(i)
    es.append('{}{:.3f},{:.3f}'.format(PainterPathElementNames[e.type], e.x, e.y))
  return 'QPainterPath<{}:{}>'.format(en, ' '.join(es))

def FormatQTransform(xform):
  "Return a string representing the QTransform's matrix"
  fmtDict = {}
  fmtFields = []
  for row in (1,2,3):
    for col in (1,2,3):
      attr = "m{}{}".format(row,col)
      fmtDict[attr] = getattr(xform, attr)()
      fmtFields.append("{"+attr+":.3f}")
  return "[{}]".format(','.join(fmtFields).format(**fmtDict))

