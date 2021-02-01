from lexer  import Token, TokenStream
from parser import ParseTree, ParseError, parse_line


class Queue:
    def __init__(self):
        pass

    def copy(self):
        pass

    def __iter__(self):
        return self

    def __next__(self):
        pass

    def __len__(self):
        n = 0
        while True:
            try:
                next(self)
                n += 1
            except StopIteration:
                break
        return n

    def __repr__(self):
        return "⟨\x1B[38;5;203mQueue\x1B[39m⟩"


class Empty(Queue):
    def __init__(self):
        pass

    def copy(self):
        return self

    def __next__(self):
        raise StopIteration

    def __repr__(self):
        return "⟨\x1B[38;5;203mQueue\x1B[39m nil⟩"

# For efficiency's sake, there's a single empty queue.
Nil = Empty()


class Literal(Queue):
    def __init__(self, lst):
        # Note that this is an actual list.
        self.list = lst
        self.index = 0

    def copy(self):
        return Literal([q.copy() for q in self.list[self.index:]])

    def __next__(self):
        if self.index < len(self.list):
            out = self.list[self.index]
            self.index += 1
            return out
        raise StopIteration

    def __repr__(self):
        q = "\x1B[38;5;203mQueue\x1B[39m"
        return f"⟨{q} literal = {self.list}⟩"


class Natural(Queue):
    def __init__(self, nat):
        self.value = nat
        self.index = 0

    def copy(self):
        return Natural(self.value - self.index)

    def __next__(self):
        if self.index < self.value:
            self.index += 1
            return Nil
        raise StopIteration

    def __repr__(self):
        q = "\x1B[38;5;203mQueue\x1B[39m"
        return f"⟨{q} natural = {self.value}⟩"


class String(Queue):
    def __init__(self, string):
        self.value = string
        self.index = 0

    def copy(self):
        return String(self.value[self.index:])

    def __next__(self):
        if self.index < len(self.value):
            out = Natural(ord(self.value[self.index]))
            self.index += 1
            return out
        raise StopIteration

    def __repr__(self):
        q = "\x1B[38;5;203mQueue\x1B[39m"
        return f"⟨{q} string = {self.value}⟩"


class SafeFactory(Queue):
    # A SafeFactory saves a copy of the template
    #   and then returns duplicates of that.
    def __init__(self, queue):
        self.queue = queue.copy()

    def copy(self):
        return self

    def __next__(self):
        return self.queue.copy()

    def __repr__(self):
        q = "\x1B[38;5;203mQueue\x1B[39m"
        return f"⟨{q} factory = {self.queue}⟩"


class UnsafeFactory(Queue):
    # An UnsafeFactory returns duplicates of
    #   the template in its current state,
    #   even if the template has changed.
    def __init__(self, queue):
        self.queue = queue

    def copy(self):
        return self

    def __next__(self):
        return self.queue.copy()

    def __repr__(self):
        q = "\x1B[38;5;203mQueue\x1B[39m"
        return f"⟨{q} factory = {self.queue}⟩"


class Concat(Queue):
    def __init__(self, fst, snd):
        self.fst = fst
        self.snd = snd

    def copy(self):
        return Concat(self.fst.copy(), self.snd.copy())

    def __next__(self):
        try:
            return next(self.fst)
        except StopIteration:
            return next(self.snd)

    def __repr__(self):
        q = "\x1B[38;5;203mQueue\x1B[39m"
        return f"⟨{q} concat = {self.fst} + {self.snd}⟩"


class Zip(Queue):
    def __init__(self, fst, snd):
        self.fst = fst
        self.snd = snd

    def copy(self):
        return Zip(self.fst.copy(), self.snd.copy())

    def __next__(self):
        # Instead of
        #
        #   try:
        #       ...
        #   except StopIteration:
        #       raise StopIteration
        #
        # we can just do
        #
        out_fst = next(self.fst)
        out_snd = next(self.snd)
        return Concat(out_fst, out_snd)

    def __repr__(self):
        q = "\x1B[38;5;203mQueue\x1B[39m"
        return f"⟨{q} zip = {self.fst} ~ {self.snd}⟩"


class Flatten(Queue):
    def __init__(self, queue):
        self.queue = queue
        self.current = Nil

    def copy(self):
        return Flatten(self.queue.copy())

    def __next__(self):
        while True:
            try:
                return next(self.current)
            except StopIteration:
                # We intentionally don't catch any StopIteration
                #   exceptions that self.queue.__next__() might throw,
                #   like we do in Zip's `next` method.
                self.current = next(self.queue)

    def __repr__(self):
        q = "\x1B[38;5;203mQueue\x1B[39m"
        return f"⟨{q} flatten = {self.queue}⟩"


class Take(Queue):
    # This kind of queue exists for debugging purposes

    def __init__(self, queue, N):
        self.queue = queue
        self.index = N
        self.halted = False

    def copy(self):
        dup = Take(self.queue.copy(), self.index)
        dup.halted = self.halted
        return dup

    def __next__(self):
        if self.index > 0:
            self.index -= 1
            return next(self.queue)
        # If there's nothing left in self.queue,
        #   this will raise a StopIteration.
        next(self.queue)
        # If we get to here, though, self.queue
        #   wasn't empty, meaning we stopped early.
        self.halted = True
        raise StopIteration

    def __repr__(self):
        q = "\x1B[38;5;203mQueue\x1B[39m"
        return f"⟨{q} take = {self.queue}⟩"


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
            raise NotImplementedError(str(node))

    elif isinstance(node, ParseTree):
        if node.kind == "literal":
            return Literal([makeQueue(elem) for elem in node.children])
        elif node.kind == "concat":
            fst = makeQueue(node.children[0])
            snd = makeQueue(node.children[1])
            return Concat(fst, snd)
        elif node.kind == "factory":
            queue = makeQueue(node.children[0])
            return SafeFactory(queue)
        elif node.kind == "zip":
            fst = makeQueue(node.children[0])
            snd = makeQueue(node.children[1])
            return Zip(fst, snd)
        elif node.kind == "flatten":
            queue = makeQueue(node.children[0])
            return Flatten(queue)
        elif node.kind == "star":
            # a*b is syntactic sugar for _(b~$a)
            fst = makeQueue(node.children[0])
            snd = makeQueue(node.children[1])
            return Flatten(Zip(snd, SafeFactory(fst)))
        else:
            raise NotImplementedError(str(node))


################################################################################


def listify(queue):
    return [listify(elem) for elem in queue]


def stirfry(queue):
    pretty = ", ".join(stirfry(q) for q in queue)
    return ("ε" if len(pretty) == 0 else "["+pretty+"]")


def zchr(n):
    return (f"\x1B[2m^{chr(64+n)}\x1B[22m" if n < 28 else chr(n))


def printNum(queue, out):
    out.write("%d\n" % len(queue))


def printStr(queue, out):
    while True:
        try:
            q = next(queue)
            out.write(zchr(len(q)))
        except StopIteration:
            out.write("\n")
            break


def printRepr(queue, out):
    out.write(", ".join(stirfry(q) for q in queue) or "ε")
    out.write("\n")


def smartPrint(queue, out):
    lst = listify(queue)
    if all(len(e) == 0 for e in lst):
        out.write("%d\n" % len(lst))
    elif all(len(s) > 0 and all(len(e)==0 for e in s) for s in lst):
        out.write("".join(zchr(len(s)) for s in lst))
        out.write("\n")
    else:
        # since stirfry actually works on lists as well
        out.write(", ".join(stirfry(e) for e in lst) or "ε")
        out.write("\n")


################################################################################


def repl():

    from sys import exit, stdout

    def prompt():
        print("\x1B[2mqn>\x1B[22m ", end='')
        line = input()
        if line in ['exit', 'quit']:
            exit()
        return line + "\n"

    stream = TokenStream("", prompt)

    try:
        while True:
            tree = parse_line(stream)
            if tree is None:
                continue
            if isinstance(tree, ParseError):
                tree.display(stream.log)
                continue
            q = makeQueue(tree)
            fq = Take(q, 1024)
            smartPrint(fq, stdout)
            if fq.halted:
                print("\x1B[93mwarning\x1B[39m: output truncated")

    except KeyboardInterrupt:
        print("\b\b")

    except EOFError:
        print('exit')


if __name__ == '__main__':
    repl()

