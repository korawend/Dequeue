from queuen.lexer import Token, TokenStream


class ParseTree:
    def __init__(self, kind, children):
        self.kind = kind            # instance of str
        self.children = children    # list of ParseTrees or literal values

    def __repr__(self):
        tk = "\x1B[38;5;128mParseTree\x1B[39m"
        return f"⟨{tk} {self.kind} = {self.children}⟩"

class ParseError:
    def __init__(self, msg, ctx):
        self.message = msg          # instance of str
        self.context = ctx          # instance of ParseTree or Token,
                                    #   or a list of ParseTrees and Tokens

    def __repr__(self):
        return "\x1B[91merror\x1B[39m: " + self.message
        # TODO this needs to be significantly improved


################################################################################


def index_token(ln, val, cls = 'delimiter'):
    idx = 0
    while idx < len(ln):
        obj = ln[idx]
        if isinstance(obj, Token) and obj.cls == cls and obj.val == val:
            return idx
        idx += 1
    return None


def rindex_token(ln, val, cls = 'delimiter'):
    idx = len(ln)-1
    while idx >= 0:
        obj = ln[idx]
        if isinstance(obj, Token) and obj.cls == cls and obj.val == val:
            return idx
        idx -= 1
    return None


def split_token(ln, val, cls = 'separator'):
    gather, run = [], []
    idx = 0
    while idx < len(ln):
        obj = ln[idx]
        if isinstance(obj, Token) and obj.cls == cls and obj.val == val:
            gather.append(run)
            run = []
        else:
            run.append(obj)
        idx += 1
    gather.append(run)
    return gather


################################################################################


# Arranged from high to low.
#   Each element looks like [op, 'unary'|'binary', 'left'|'right'].
#
OperatorPrecedence = []


# Returns None, an instance of ParseTree, or an instance of ParseError.
#
def _parse(line):

    if len(line) == 0:
        return None

    while (lp := index_token(line, "(")) is not None:
        rp = index_token(line, ")")
        if (rp is not None) and rp < lp:
            return ParseError("missing left parenthesis", line)
        height = 1
        rp = lp + 1
        while True:
            if rp >= len(line):
                return ParseError("missing right parenthesis", line)
            obj = line[rp]
            if isinstance(obj, Token) and obj.cls == 'delimiter':
                if obj.val == '(': height += 1
                if obj.val == ')': height -= 1
            if height == 0: break
            rp += 1

        interior = _parse(line[lp+1:rp])
        if interior is None:
            return ParseError("nothing to parse inside parentheses", None)
        if isinstance(interior, ParseError):
            return interior

        line = line[:lp] + [interior] + line[rp+1:]

    # And now, at this point, we're guaranteed that aren't any parentheses.
    # First, construct queue literals.

    while (lb := index_token(line, "[")) is not None:
        rb = index_token(line, "]")
        if (rb is not None) and rb < lb:
            return ParseError("missing left bracket", line)
        height = 1
        rb = lb + 1
        while True:
            if rb >= len(line):
                return ParseError("missing right bracket", line)
            obj = line[rb]
            if isinstance(obj, Token) and obj.cls == 'delimiter':
                if obj.val == '[': height += 1
                if obj.val == ']': height -= 1
            if height == 0: break
            rb += 1

        elems = split_token(line[lb+1:rb], ",")
        interior = []
        for elem in elems:
            parsed_elem = _parse(elem)
            if isinstance(parsed_elem, ParseError):
                return parsed_elem
            interior.append(parsed_elem)

        if len(interior) < 1:
            raise Exception("this should never happen")

        elif len(interior) == 1:
            if interior[0] is None:
                interior = []

        elif len(interior) > 1:
            if None in interior:
                pass    # TODO what should actually happen here? e.g. [0,,0]

        literal = ParseTree('literal', interior)
        line = line[:lb] + [literal] + line[rb+1:]

    # At this point, we're guaranteed that aren't any parentheses or brackets.
    # Second, complain about any braces, since they don't do anything yet.

    if (index_token(line, "{") is not None) or (index_token(line, "}") is not None):
        return ParseError('illegal delimiter', line)

    # Third, parse operators.
    # TODO

    # And we're all done!
    if len(line) > 1:
      return line   # TODO what should actually happen here?

    return line[0]


def parse_line(stream):
    # read until we encounter a newline
    line = []
    while True:
        tok = next(stream)
        if (tok is None) or (tok.cls == 'newline'):
            break
        line.append(tok)

    return _parse(line)


################################################################################


def prompt():
    print("queuen> ", end='')
    return input() + "\n"

stream = TokenStream("", prompt)
while True:
    ln = parse_line(stream)
    print(ln)

