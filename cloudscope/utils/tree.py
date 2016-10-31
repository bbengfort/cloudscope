# -*- coding: utf-8 -*-
# cloudscope.utils.tree
# Utility module that implements a Tree data structure.
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Sep 27 11:40:20 2016 -0400
#
# Copyright (C) 2016 University of Maryland
# For license information, see LICENSE.txt
#
# ID: tree.py [] benjamin@bengfort.com $

"""
Utility module that implements a Tree data structure.
"""

##########################################################################
## Imports
##########################################################################

from __future__ import division

from peak.util.imports import lazyModule

# Lazy load visualizations
gt  = lazyModule('graph_tool.all')


##########################################################################
## Trees
##########################################################################

class Tree(object):
    """
    A Tree object is essentially a label and a list of children that can
    themselves be Tree objects. Trees implement bidirectionality with pointers
    to both their parent and the children. Any Tree without a parent is
    considered to be a root node.

    Trees can also maintain any arbitrary data behond their label.
    """

    # Label for the root node.
    ROOT = 'root'

    @classmethod
    def from_version(cls, vers):
        """
        Constructs the tree from a version object.
        """
        tree = cls(str(vers.version), name=vers.name)
        for child in vers.children:
            tree.append(cls.from_version(child))
        return tree

    def __init__(self, label=ROOT, children=None, parent=None, **data):
        self.label    = label
        self.data     = data
        self.parent   = parent
        self.children = []

        # Add children passed into the Tree.
        if children is not None:
            for child in children:
                self.append(child)

    #////////////////////////////////////////////////////////////
    # Verification Mechanisms
    #////////////////////////////////////////////////////////////

    def is_root(self):
        """
        The tree is not a subtree if it has no parent node.
        """
        return self.parent is None

    def is_leaf(self):
        """
        The subtree is a terminal if it has no children.
        """
        return len(self.children) == 0

    #////////////////////////////////////////////////////////////
    # Basic tree operations
    #////////////////////////////////////////////////////////////

    def append(self, child, **data):
        """
        Add a child to the tree, associating the parent and converting to the
        correct data structure.
        """
        if not isinstance(child, Tree):
            child = type(self)(label=child, **data)

        child.parent = self
        self.children.append(child)
        return child

    def leaves(self):
        """
        Returns a list of all the leaf nodes of the tree.
        """
        leaves = []
        for child in self:
            if child.is_leaf():
                leaves.append(child)
            else:
                leaves.extend(child.leaves())
        return leaves

    def flatten(self):
        """
        Returns a flat version of the tree with all non-root non-terminals
        removed such that all the children from the subtree are leaves.
        """
        return Tree(self.label, self.leaves(), **self.data)

    def subtrees(self, filter=None):
        """
        Generate all the subtrees of this tree, optionally restricted to
        trees matching the supplied filter function.
        """
        if not filter or filter(self):
            yield self
        for child in self.children:
            if isinstance(child, Tree):
                for subtree in child.subtrees(filter):
                    yield subtree

    def height(self):
        """
        Returns the height of the tree.

        The height of a tree with no children is 1; the height of a tree with
        only leaves is 2; and the height of any other tree is one plus the
        maximum of its children's heights.
        """
        max_child_height = 0
        for child in self.children:
            if child.is_leaf():
                max_child_height = max(max_child_height, 1)
            else:
                max_child_height = max(max_child_height, child.height())
        return 1 + max_child_height

    def depth(self):
        """
        Returns the depth of this subtree from the root.
        """
        if self.is_root():
            return 0
        return 1 + self.parent.depth()

    def size(self):
        """
        Returns the number of nodes for this subtree. The size of the tree is
        1 + the sum of the sizes of all its children.
        """
        return 1 + sum(child.size() for child in self.children)

    def forks(self):
        """
        Returns the number of branches in the tree. If a node has zero or one
        child, then the number of forks is 0 + the number of forks for its
        children. If the node has 2 or more children, then the number of forks
        is equal to one less the number of children + the number of forks for
        all its children.
        """
        forks = 0 if len(self.children) < 2 else len(self.children) - 1
        return forks + sum(child.forks() for child in self.children)

    #////////////////////////////////////////////////////////////
    # Helper functions
    #////////////////////////////////////////////////////////////

    # Print constants
    ITEM   = u"├─ "
    INDENT = u"   "
    LAST   = u"└─ "

    def pprint(self, depth=-1, last=False):
        """
        Unicode representation of the tree.
        """
        sep = self.LAST if last else self.ITEM
        sep = "" if depth < 0 else sep
        ind = self.INDENT*depth
        rep = u"{}{}{}\n".format(ind, sep, self.label)

        for idx, child in enumerate(self.children):
            is_last = idx == (len(self.children)-1)
            rep += child.pprint(depth+1, is_last)

        return rep

    def to_graph(self, name=None):
        """
        Returns the graph tool graph from the Tree.
        """
        g = gt.Graph()

        # Add the graph name
        g.gp.name = g.new_graph_property('string')
        g.gp.name = name or "{} Graph Construction".format(self.__class__.__name__)

        # Add vertex and edge properties
        g.vp.label = g.new_vertex_property('string')

        def add_node(g, node):
            """
            Recursive vertex constructor to add node and all children.
            """
            parent = g.add_vertex()
            g.vp.label[parent] = node.label

            # Depth first construction
            for child in node.children:
                child = add_node(g, child)
                g.add_edge(child, parent)

            return parent

        # Start DFS node addition
        add_node(g, self)
        return g

    def draw(self, name=None, **kwargs):
        """
        Uses graph tool to draw the graph.
        """
        g = self.to_graph(name)

        defaults = {
            'vertex_text': g.vp.label,
            'vertex_pen_width': 1,
            'vertex_fill_color': [0x37 / 0xff, 0x78 / 0xff, 0xbf / 0xff, 0.85],
            'vertex_size': 25,
            'vertex_font_weight': 1,
            'vertex_font_size': 12,
            'edge_pen_width': 2,
        }
        defaults.update(kwargs)

        gt.graph_draw(g, **defaults)

    #////////////////////////////////////////////////////////////
    # Collection Data Model
    #////////////////////////////////////////////////////////////

    def __iter__(self):
        for child in self.children:
            yield child

    def __eq__(self, other):
        """
        Equality only requires the label and the list of children to be
        identical. The parent node and any associated data are ignored. Also
        they have to be of the same type.
        """
        return (
            self.__class__ is other.__class__ and
            (self.label, list(self)) == (other.label, list(other))
        )

    __ne__ = lambda self, other: not self == other
