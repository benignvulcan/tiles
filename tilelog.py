#!/usr/bin/env python3
'''
Python 3.4 Logging Formatting Is Nearly Broken
==============================================

Python 3 encourages us to use '{}'.format() instead of the traditional '%' formatting.  It's better.

Except for logging.

The Python 'logging' library was designed with '%' formatting deeply embedded into it, and was also designed to be global in a non-modular way, making fixing it to use str.format formatting quite difficult.

Formatting of records is split between LogRecord, which formats arguments to Logger.log() (and .debug(), .info(), .warn(), .error(), .critical() and their logging module-level counterparts), and LogRecord.__init__(), and Formatter, which takes the resulting "messagae" string and generates an entire log entry indicating the logging level, module name, timestamp, or whatever, in addition to the core message.

The overall formatting can be specified using a '%' format string, and as of Python 3.2 can be also specified with a '{}' format string.  Typically it would only be called from one or two locations, and is not a big deal.

But the formatting to Logger.log() can only be specified on EACH AND EVERY CALL, unless the programmer is willing to:
  - write separate wrapper code
  - override Logger and/or LogRecord GLOBALLY, potentially breaking any module anywhere unless great care is taken to only provide "alternate" str.format to those callers that want it, somehow...
    * LogRecord would have to be subclassed to provide str.format behavior, or combination str.format / '%' behavior.
    * But Logger would almost certainly have to be subclassed to provide the ability of some callers to generate str.format LogRecords while still automatically being backwards compatible for any client that doesn't know about it.
    * which requires dealing with global allocation of Loggers...

--------

And none of the above deals with what in my view should have been an obviously desirable feature: trace() level logging (below debug()) and output indentation of such to reflect call stack depth.  It does look as though a sophisticated programmer could customize Formatter to do this using the available stack data, or by getting it from the 'inspect' module.

--------

So I'm not willing to fix all that for such a modest project.
'''

import inspect as _inspect
import os as _os

class NotLogger(object):

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self._baseline = len(_inspect.stack())
    # A fixed set of logging levels doesn't permit inserting new levels easily.
    # Just use names.
    # Not currently efficient at all.
    self._levels = 'all trace debug info warning error critical'.split()
    self.setFilterLevel('warning')

  def getLevel(self, levelName):
    for i in range(len(self._levels)):
      if self._levels[i] == levelName:
        return i
    raise TypeError("unregistered logging level")

  def setFilterLevel(self, levelName):
    self._lvl = self.getLevel(levelName)

  def isEnabledFor(self, levelName):
    return self.getLevel(levelName) >= self._lvl

  def log(self, lvl, msg='', *posargs, **kwargs):
    if lvl >= self._lvl:
      message = msg.format(*posargs, **kwargs)
      levelName = self._levels[lvl].upper()
      stack = _inspect.stack()
      indent = '. ' * (len(stack) - self._baseline - 1)
      frec = stack[2]
      filename = _os.path.basename(frec[1])
      if filename.endswith('.py'): filename = filename[:-3]
      funcname = frec[3]
      #frame = frec[0]
      #funcname = _inspect.getframeinfo(frame).function
      print('{}{}:{}:{}:{}'.format(indent, levelName, filename, funcname, message))
      del frec, stack

  def trace     (self, *posargs, **kwargs): return self.log(self.getLevel('trace'   ), *posargs, **kwargs)
  def debug     (self, *posargs, **kwargs): return self.log(self.getLevel('debug'   ), *posargs, **kwargs)
  def info      (self, *posargs, **kwargs): return self.log(self.getLevel('info'    ), *posargs, **kwargs)
  def warning   (self, *posargs, **kwargs): return self.log(self.getLevel('warning' ), *posargs, **kwargs)
  def error     (self, *posargs, **kwargs): return self.log(self.getLevel('error'   ), *posargs, **kwargs)

def _selftest():
  logger = NotLogger()
  logger.info('self info')
  logger.warning('this should be the first visible message')
  logger.setFilterLevel('trace')
  logger.info('self info 2')

if __name__=='__main__': _selftest()
