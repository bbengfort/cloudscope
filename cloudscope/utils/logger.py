# cloudscope.utils.logger
# Wraps the Python logging module for cloudscope-specific logging.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Dec 09 13:10:59 2015 -0500
#
# Copyright (C) 2015 University of Maryland
# For license information, see LICENSE.txt
#
# ID: logger.py [] benjamin@bengfort.com $

"""
Wraps the Python logging module for cloudscope-specific logging.
"""

##########################################################################
## Imports
##########################################################################

import getpass
import logging
import warnings
import logging.config

from cloudscope.config import settings
from cloudscope.dynamo import Sequence

##########################################################################
## Logging configuration: must be run at the module level first
##########################################################################

configuration = {
    'version': 1,
    'disable_existing_loggers': settings.logging.disable_existing_loggers,

    'formatters': {
        'simple': {
            'format':  settings.logging.logfmt,
            'datefmt': settings.logging.datefmt,
        },
        'simulation': {
            'format':  "[%(time)7d] %(message)s",
            'datefmt': settings.logging.datefmt,
        },
    },

    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'simulation': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simulation',
        },
    },

    'loggers':  {
        'cloudscope': {
            'level': settings.logging.level,
            'handlers': ['console',],
            'propagate': True,
        },
        'cloudscope.server': {
            'level': settings.logging.level,
            'handlers': ['console',],
            'propagate': False,
        },
        'cloudscope.simulation': {
            'level': settings.logging.level,
            'handlers': ['simulation',],
            'propagate': False,
        },
        'py.warnings': {
            'level': 'DEBUG',
            'handlers': ['console',],
            'propagate': True,
        },
    },
}

logging.config.dictConfigClass(configuration).configure()
if not settings.debug: logging.captureWarnings(True)

##########################################################################
## Logger utility
##########################################################################

class WrappedLogger(object):
    """
    Wraps the Python logging module's logger object to ensure that all simulation
    logging happens with the correct configuration as well as any extra
    information that might be required by the log file (for example, the user
    on the machine, hostname, IP address lookup, etc).

    Subclasses must specify their logger as a class variable so all instances
    have access to the same logging object.
    """

    logger = None

    def __init__(self, **kwargs):
        self.raise_warnings = kwargs.pop('raise_warnings', settings.debug)
        self.logger = kwargs.pop('logger', self.logger)

        if not self.logger or not hasattr(self.logger, 'log'):
            raise TypeError(
                "Subclasses must specify a logger, not {}"
                .format(type(self.logger))
            )

        self.extras = kwargs

    def log(self, level, message, *args, **kwargs):
        """
        This is the primary method to override to ensure logging with extra
        options gets correctly specified.
        """
        extra = self.extras.copy()
        extra.update(kwargs.pop('extra', {}))

        kwargs['extra'] = extra
        self.logger.log(level, message, *args, **kwargs)

    def debug(self, message, *args, **kwargs):
        return self.log(logging.DEBUG, message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        return self.log(logging.INFO, message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        """
        Specialized warnings system. If a warning subclass is passed into
        the keyword arguments and raise_warnings is True - the warnning will
        be passed to the warnings module.
        """
        warncls = kwargs.pop('warning', None)
        if warncls and self.raise_warnings:
            warnings.warn(message, warncls)

        return self.log(logging.WARNING, message, *args, **kwargs)

    # Alias warn to warning
    warn = warning

    def error(self, message, *args, **kwargs):
        return self.log(logging.ERROR, message, *args, **kwargs)

    def critical(self, message, *args, **kwargs):
        return self.log(logging.CRITICAL, message, *args, **kwargs)

##########################################################################
## The web server logger class
##########################################################################

class ServerLogger(WrappedLogger):
    """
    Usage:

        >>> from cloudscope.utils.logger import ServerLogger
        >>> logger = ServerLogger()
        >>> logger.info("You were here!")

    This will correctly log messages from the web server.
    """

    logger  = logging.getLogger('cloudscope.server')

    def log(self, level, message, *args, **kwargs):
        """
        Provide current user as extra context to the logger
        """
        # No extra context required at the moment.
        super(ServerLogger, self).log(level, message, *args, **kwargs)


##########################################################################
## The simulation logger class
##########################################################################

class SimulationLogger(WrappedLogger):
    """
    This will correctly log messages from the simulation.
    """

    counter = Sequence()
    logger  = logging.getLogger('cloudscope.simulation')

    def __init__(self, env, **kwargs):
        self.env   = env
        self._user = kwargs.pop('user', None)
        super(SimulationLogger, self).__init__(**kwargs)

    @property
    def user(self):
        if not self._user:
            self._user = getpass.getuser()
        return self._user

    def log(self, level, message, *args, **kwargs):
        """
        Provide current user as extra context to the logger
        """
        extra = kwargs.pop('extra', {})
        extra.update({
            'user':  self.user,
            'msgid': self.counter.next(),
            'time':  self.env.now,
        })

        kwargs['extra'] = extra
        super(SimulationLogger, self).log(level, message, *args, **kwargs)


if __name__ == '__main__':
    logger = ServerLogger()
    logger.debug("This is just a test.")
    logger.info("Canaries can fly carrying coconuts.")
    logger.warning("Beware ducks that dont' blink.")
    logger.error("I can't do that, Dave.")
    logger.critical("The pressure doors are open!")
