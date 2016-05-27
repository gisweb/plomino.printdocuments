# -*- coding: utf-8 -*-
"""Setup tests for this package."""
from plomino.printdocuments.testing import PLOMINO_PRINTDOCUMENTS_INTEGRATION_TESTING  # noqa
from plone import api

import unittest2 as unittest


class TestSetup(unittest.TestCase):
    """Test that plomino.printdocuments is properly installed."""

    layer = PLOMINO_PRINTDOCUMENTS_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')

    def test_product_installed(self):
        """Test if plomino.printdocuments is installed with portal_quickinstaller."""
        self.assertTrue(self.installer.isProductInstalled('plomino.printdocuments'))

    def test_browserlayer(self):
        """Test that IPlominoPrintdocumentsLayer is registered."""
        from plomino.printdocuments.interfaces import IPlominoPrintdocumentsLayer
        from plone.browserlayer import utils
        self.assertIn(IPlominoPrintdocumentsLayer, utils.registered_layers())


class TestUninstall(unittest.TestCase):

    layer = PLOMINO_PRINTDOCUMENTS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')
        self.installer.uninstallProducts(['plomino.printdocuments'])

    def test_product_uninstalled(self):
        """Test if plomino.printdocuments is cleanly uninstalled."""
        self.assertFalse(self.installer.isProductInstalled('plomino.printdocuments'))
