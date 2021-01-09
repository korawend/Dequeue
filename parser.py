import lexer

class ParseTree:
    def __init__(self, name, leaf, children):
        self.name = name            # the name or label of the node; an instance of str
        self.leaf = leaf            # True if this is a leaf (children are Tokens), else False
        self.children = children    # list of ParseTrees or a list of Tokens

