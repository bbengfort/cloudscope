# tests.test_utils.test_tree
# Tests for the Tree data structure utility.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Wed Sep 28 08:30:45 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: test_tree.py [] benjamin@bengfort.com $

"""
Tests for the Tree data structure utility.
"""

##########################################################################
## Imports
##########################################################################

import unittest

from cloudscope.utils.tree import *
from cloudscope.replica import Replica, Version

try:
    from unittest import mock
except ImportError:
    import mock

##########################################################################
## Tree Class Tests
##########################################################################

class TreeTests(unittest.TestCase):

    def test_tree_construction(self):
        """
        Test Tree construction from initialization.
        """

        tree = Tree('A', [Tree('B', ['C', 'D']), Tree('E', [Tree('F', []), 'G'])])

        self.assertTrue(tree.is_root())

        for subtree in tree.subtrees(lambda t: t.label != 'A'):
            self.assertFalse(subtree.is_root())
            self.assertIsNotNone(subtree.parent)
            self.assertIsInstance(subtree.parent, Tree)

    def test_is_root(self):
        """
        Test the is root test method on a Tree
        """
        tree = Tree('A')
        self.assertTrue(tree.is_root())

        child = Tree('B')
        self.assertTrue(child.is_root())
        tree.append(child)
        self.assertFalse(child.is_root())
        self.assertTrue(tree.is_root())

        child.append('C')
        self.assertFalse(child.children[0].is_root())
        self.assertFalse(child.is_root())
        self.assertTrue(tree.is_root())

    def test_is_leaf(self):
        """
        Test the is leaf test method on a Tree
        """
        tree = Tree('A')
        self.assertTrue(tree.is_leaf())

        child = Tree('B')
        self.assertTrue(child.is_leaf())
        tree.append(child)
        self.assertTrue(child.is_leaf())
        self.assertFalse(tree.is_leaf())

        child.append('C')
        for grandchild in child.children:
            self.assertTrue(grandchild.is_leaf())
        self.assertFalse(child.is_leaf())
        self.assertFalse(tree.is_leaf())

        child.append('D')
        for grandchild in child.children:
            self.assertTrue(grandchild.is_leaf())
        self.assertFalse(child.is_leaf())
        self.assertFalse(tree.is_leaf())

        child.append('E')
        for grandchild in child.children:
            self.assertTrue(grandchild.is_leaf())
        self.assertFalse(child.is_leaf())
        self.assertFalse(tree.is_leaf())

        child = Tree('F')
        tree.append(child)
        self.assertFalse(tree.is_leaf())
        self.assertTrue(child.is_leaf())

    def test_child_append(self):
        """
        Assert that all Tree append operations work as expected
        """
        tree = Tree('A')
        self.assertEqual(len(tree.children), 0)

        child = tree.append('B')
        self.assertIsInstance(child, Tree)
        self.assertEqual(child.parent, tree)

        child = tree.append(Tree('C'))
        self.assertIsInstance(child, Tree)
        self.assertEqual(child.parent, tree)

    def test_leaves_fetch(self):
        """
        Test the leaf nodes extraction operation.
        """

        tree = Tree('A', [Tree('B', ['C', 'D']), Tree('E', [Tree('F', []), 'G'])])
        leaves = ['C', 'D', 'F', 'G']

        self.assertEqual([l.label for l in tree.leaves()], leaves)
        child = tree.append('H')

        leaves = ['C', 'D', 'F', 'G', 'H']
        self.assertEqual([l.label for l in tree.leaves()], leaves)

        child.append('I')
        leaves = ['C', 'D', 'F', 'G', 'I']
        self.assertEqual([l.label for l in tree.leaves()], leaves)

    def test_flatten(self):
        """
        Test the flatten Tree operation
        """
        tree = Tree('A', [Tree('B', ['C', 'D']), Tree('E', [Tree('F', []), 'G'])])
        flat = Tree('A', ['C', 'D', 'F', 'G'])
        self.assertEqual(tree.flatten(), flat)

    def test_height_size(self):
        """
        Test the height and size computation
        """
        tree = Tree()

        # Create the "A" branch
        child = tree
        for idx in xrange(5):
            child = child.append("a{}".format(idx))

        self.assertEqual(tree.height(), 6)
        self.assertEqual(tree.size(), 6)

        # Create the "B" branch
        child = tree
        for idx in xrange(8):
            child = child.append("b{}".format(idx))

        self.assertEqual(tree.height(), 9)
        self.assertEqual(tree.size(), 14)

        # Create the "C" branch
        child = tree
        for idx in xrange(6):
            child = child.append("c{}".format(idx))

        self.assertEqual(tree.height(), 9)
        self.assertEqual(tree.size(), 20)

        # Extend the "A" branch
        child = tree.leaves()[0]
        for idx in xrange(12):
            child = child.append("a{}".format(idx))

        self.assertEqual(tree.height(), 18)
        self.assertEqual(tree.size(), 32)

    def test_depth_computation(self):
        """
        Test the depth computation from children
        """
        tree = Tree()
        self.assertEqual(tree.depth(), 0)

        # Create the "A" branch
        child = tree
        for idx in xrange(3):
            child = child.append("a{}".format(idx))
            self.assertEqual(child.depth(), idx+1)

        # Create the "B" branch
        child = tree
        for idx in xrange(6):
            child = child.append("a{}".format(idx))
            self.assertEqual(child.depth(), idx+1)

        # Fork the "A" branch
        child = tree.children[0]
        for idx in xrange(2):
            sib = child.parent.append("a{}-sib".format(idx))
            self.assertEqual(child.depth(), sib.depth())
            child = child.children[0]

    def test_forks_computation(self):
        """
        Test computing forks on a Tree
        """
        tree = Tree()
        self.assertEqual(tree.forks(), 0)

        child = tree.append("A")
        self.assertEqual(tree.forks(), 0)
        self.assertEqual(child.forks(), 0)

        child = tree.append("B")
        self.assertEqual(tree.forks(), 1)
        self.assertEqual(child.forks(), 0)

        gchild = child.append("C")
        self.assertEqual(tree.forks(), 1)
        self.assertEqual(child.forks(), 0)
        self.assertEqual(gchild.forks(), 0)

        gchild = child.append("D")
        self.assertEqual(tree.forks(), 2)
        self.assertEqual(child.forks(), 1)
        self.assertEqual(gchild.forks(), 0)

        gchild = child.append("E")
        self.assertEqual(tree.forks(), 3)
        self.assertEqual(child.forks(), 2)
        self.assertEqual(gchild.forks(), 0)

        ggchild = gchild.append("F")
        self.assertEqual(tree.forks(), 3)
        self.assertEqual(child.forks(), 2)
        self.assertEqual(gchild.forks(), 0)
        self.assertEqual(ggchild.forks(), 0)

        ggchild = gchild.append("H")
        self.assertEqual(tree.forks(), 4)
        self.assertEqual(child.forks(), 3)
        self.assertEqual(gchild.forks(), 1)
        self.assertEqual(ggchild.forks(), 0)


    def test_construct_from_version(self):
        """
        Test Tree instantiation from a version.
        """
        # Set up a mock simulation
        sim = mock.MagicMock()
        sim.env.now  = 42
        r0, r1 = Replica(sim), Replica(sim)
        sim.replicas = [r0, r1]

        # Create a new version
        Foo = Version.new("Foo")

        # Add some version history
        f1 = Foo(r0)
        f2 = f1.nextv(r0)
        f3 = f1.nextv(r1)
        f4 = f2.nextv(r0)
        f5 = f3.nextv(r1)
        f6 = f5.nextv(r1)
        f7 = f6.nextv(r1)
        f8 = f7.nextv(r0)

        tree = Tree.from_version(f1)
        self.assertTrue(tree.is_root())
        self.assertEqual(tree.label, '1')
        self.assertEqual(tree.data['name'], 'Foo')
        self.assertEqual(tree.height(), 6)
        self.assertEqual(tree.size(), 8)

        def evaluate(parent):
            for child in parent:
                self.assertEqual(child.parent, parent)
                self.assertIsInstance(child.label, str)
                self.assertEqual(child.data['name'], parent.data['name'])
                self.assertGreater(int(child.label), int(parent.label))
                evaluate(child)

        evaluate(tree)
