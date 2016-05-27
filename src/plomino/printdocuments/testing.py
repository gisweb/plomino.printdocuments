# -*- coding: utf-8 -*-
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2

import plomino.printdocuments


class PlominoPrintdocumentsLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        self.loadZCML(package=plomino.printdocuments)

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'plomino.printdocuments:default')


PLOMINO_PRINTDOCUMENTS_FIXTURE = PlominoPrintdocumentsLayer()


PLOMINO_PRINTDOCUMENTS_INTEGRATION_TESTING = IntegrationTesting(
    bases=(PLOMINO_PRINTDOCUMENTS_FIXTURE,),
    name='PlominoPrintdocumentsLayer:IntegrationTesting'
)


PLOMINO_PRINTDOCUMENTS_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(PLOMINO_PRINTDOCUMENTS_FIXTURE,),
    name='PlominoPrintdocumentsLayer:FunctionalTesting'
)


PLOMINO_PRINTDOCUMENTS_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        PLOMINO_PRINTDOCUMENTS_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE
    ),
    name='PlominoPrintdocumentsLayer:AcceptanceTesting'
)
