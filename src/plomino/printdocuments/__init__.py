# -*- coding: utf-8 -*-
"""Init and utils."""

from zope.i18nmessageid import MessageFactory
from AccessControl import allow_module

_ = MessageFactory('plomino.printdocuments')

allow_module("plomino.printdocuments.serialdoc")
