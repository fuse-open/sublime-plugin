import unittest
try:
    from .fuse_util import *
except:
    from fuse_util import *

class TestFuseUtil(unittest.TestCase):

    def test_getExtension(self):
        self.assertEqual(getExtension(None), "")
        self.assertEqual(getExtension(""), "")
        self.assertEqual(getExtension("foo.ux"), "ux")
        self.assertEqual(getExtension("foo/bar.ux"), "ux")
        self.assertEqual(getExtension(".profile"), "")

    def test_isSupportedSyntax(self):
        self.assertTrue(isSupportedSyntax("Uno"))
        self.assertTrue(isSupportedSyntax("UX"))

        self.assertFalse(isSupportedSyntax("uno"))
        self.assertFalse(isSupportedSyntax(".uno"))
        self.assertFalse(isSupportedSyntax(""))
        self.assertFalse(isSupportedSyntax(None))
        self.assertFalse(isSupportedSyntax(42))

    def test_getSyntax(self):
        self.assertEqual(getSyntax(MockSettingsView("Packages/Fuse/UX.tmLanguage")), "UX")
        self.assertEqual(getSyntax(MockSettingsView("Packages/Fuse/Uno.tmLanguage")), "Uno")

    def test_getRowCol(self):
        self.assertEqual( {"Line": 21, "Character": 31}, getRowCol(MockRowColView(), 10))

class MockSettingsView:
    def __init__(self, language):
        self.language = language

    def settings(self):
        return {"syntax" :self.language}

class MockRowColView:
    def rowcol(self, pos):
        return (pos + 10, pos + 20)
