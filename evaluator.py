from lexer  import Token, TokenStream
from parser import ParseTree, ParseError, parse_line


class Queue:
    def __init__(self):
        pass

    def copy(self):
        pass

    def next(self):
        pass


class Empty(Queue):
    def __init__(self):
        pass

    def copy(self):
        return self

    def next(self):
        raise StopIteration

# For efficiency's sake, there's a single empty queue.
Nil = Empty()


class Literal(Queue):
    def __init__(self, lst):
        # Note that this is an actual list.
        self.list = lst
        self.index = 0

    def copy(self):
        return Literal(self.list)

    def next(self):
        if self.index < len(self.list):
            out = self.list[self.index]
            self.index += 1
            return out
        raise StopIteration


class Natural(Queue):
    def __init__(self, nat):
        self.value = nat
        self.index = 0

    def copy(self):
        return Natural(self.value)

    def next(self):
        if self.index < self.value:
            self.index += 1
            return Nil
        raise StopIteration


class String(Queue):
    def __init__(self, string):
        self.value = string
        self.index = 0

    def copy(self):
        return String(self.value)

    def next(self):
        if self.index < len(self.value):
            out = Natural(ord(self.value[self.index]))
            self.index += 1
            return out
        raise StopIteration


class Factory(Queue):
    def __init__(self, queue):
        # Should we instead make a copy of queue?
        self.queue = queue

    def copy(self):
        return Factory(self.queue)

    def next(self):
        return self.queue.copy()


class Concat(Queue):
    def __init__(self, fst, snd):
        # Should we instead use copies of fst and snd?
        self.fst = fst
        self.snd = snd

    def copy(self):
        return Concat(self.fst, self.snd)

    def next(self):
        try:
            return self.fst.next()
        except StopIteration:
            return self.snd.next()


class Zip(Queue):
    def __init__(self, fst, snd):
        # Should we instead use copies of fst and snd?
        self.fst = fst
        self.snd = snd

    def copy(self):
        return Zip(self.fst, self.snd)

    def next(self):
        # Instead of
        #
        #   try:
        #       ...
        #   except StopIteration:
        #       raise StopIteration
        #
        # we can just do
        #
        out_fst = self.fst.next()
        out_snd = self.snd.next()
        return Concat(out_fst, out_snd)


class Flatten(Queue):
    def __init__(self, queue):
        # Should we instead use a copy of queue?
        self.queue = queue
        self.current = Nil

    def copy(self):
        return Flatten(self.queue)

    def next(self):
        while True:
            try:
                return self.current.next()
            except StopIteration:
                # We intentionally don't catch any StopIteration
                #   exceptions that self.queue.next() might throw,
                #   like we do in Zip's `next` method.
                self.current = self.queue.next()


################################################################################

# Token: 'natural', 'string'
# ParseTree: 'literal', 'factory', 'flatten', 'zip', 'concat'

def makeQueue(node):
    if isinstance(node, Token):
        if node.cls == "natural":
            return Natural(node.val)
        elif node.cls == "string":
            return String(node.val)
        else:
            raise NotImplementedError

    elif isinstance(node, ParseTree):
        if node.kind == "literal":
            return Literal([makeQueue(elem) for elem in node.children])
        elif node.kind == "concat":
            fst = makeQueue(node.children[0])
            snd = makeQueue(node.children[1])
            return Concat(fst, snd)
        elif node.kind == "factory":
            queue = makeQueue(node.children[0])
            return Factory(queue)
        elif node.kind == "zip":
            fst = makeQueue(node.children[0])
            snd = makeQueue(node.children[1])
            return Zip(fst, snd)
        elif node.kind == "flatten":
            queue = makeQueue(node.children[0])
            return Flatten(queue)
        else:
            raise NotImplementedError


################################################################################


def printNum(queue, out):
    n = 0
    while True:
        try:
            queue.next()
            n += 1
        except StopIteration:
            break
    out.write("%d\n" % n)


def printStr(queue, out):
    while True:
        try:
            sub = queue.next()
        except StopIteration:
            out.write("\n")
            break
        n = 0
        while True:
            try:
                sub.next()
                n += 1
            except StopIteration:
                break
        out.write(chr(n))


def listify(queue):
    lst = []
    while True:
        try:
            elem = queue.next()
            lst.append(listify(elem))
        except StopIteration:
            return lst


def printRepr(queue, out):
    out.write(str(listify(queue)))
    out.write("\n")


################################################################################


def repl():

    from sys import exit, stdout

    def prompt():
        print("\x1B[2mqueuen>\x1B[22m ", end='')
        line = input()
        if line in ['exit', 'quit']:
            exit()
        return line + "\n"

    stream = TokenStream("", prompt)

    try:
        while True:
            tree = parse_line(stream)
            if isinstance(tree, ParseError):
                tree.display(stream.log)
                continue
            q = makeQueue(tree)
            printNum(q, stdout)

    except KeyboardInterrupt:
        print("\b\b")

    except EOFError:
        print('exit')


if __name__ == '__main__':
    repl()
