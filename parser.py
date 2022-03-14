from lexer import Token, TokenStream

# For a fun example of the debug output, set DEBUG = True and then enter these
#  literals at the prompt:
#
# [[[[[[], [[[]]], []], []], [[[[[], []]]], [[[[], [], [[]]], []]]], [[[]]]], []]]
# [[[[], [[]], [[[[]], [], [[[[]], [], []]]]]], [[[[[]], []], [], [[[]]]], [[]]]]]
# [[[], [[[], [[[[[]], [], []]]]], [], []]], [[[]], [[], []], [[], [], []]], []]
#
DEBUG = False


# The token classes are  newline   ,  natural ,  string    ,
#                        delimiter ,  special ,  separator ,  operator
#                        keyword   ,  name

class ParseTree:
    def __init__(self, kind, children):
        self.kind = kind            # instance of str
        self.children = children    # list of ParseTrees or Tokens

    def __repr__(self):
        tk = "\x1B[38;5;129mParseTree\x1B[39m"
        return f"⟨{tk} {self.kind} = {self.children}⟩"


def extract_tokens(obj):
    if isinstance(obj, Token):
        return [obj]
    if isinstance(obj, ParseTree):
        obj = obj.children
    if isinstance(obj, list):
        out = []
        for x in obj:
            out += extract_tokens(x)
        return out
    return []


class ParseError:
    def __init__(self, msg, hi, redux = False):
        self.message   = msg        # instance of str
        self.highlight = hi         # instance of ParseTree or Token,
                                    #   or a list of ParseTrees and Tokens
        self.redux     = redux      # whether this is a reducibility error

    def __repr__(self):
        return "\x1B[91merror\x1B[39m: " + self.message

    def display(self, log):
        tokens = extract_tokens(self.highlight)
        if len(tokens) < 1:
            print("\x1B[91merror\x1B[39m: " + self.message)
            return
        top = tokens[0].ln - 1
        bot = tokens[-1].ln - 1
        if bot-top > 1:
            return  # not sure how to display multi-line errors
                    #   (but fortunately, there aren't any yet)
        print(f"\x1B[91merror\x1B[39m: line {tokens[0].ln}: " + self.message)
        line = (log.split("\n"))[top]
        margin = "\x1B[2m\u2502\x1B[22m "
        print(margin)
        print(margin + line)
        if not self.redux:
            left = tokens[0].col - 1                         # inclusive
            right = tokens[-1].col - 1 + len(tokens[-1].txt) # exclusive
            print(margin + " "*left + "\x1B[91m^", end='')
            print("~"*(right-left-1), end='')
            print("\x1B[39m")
        else:
            print(margin, end='')
            colors = ["\x1B[94m", "\x1B[93m", "\x1B[96m", "\x1B[95m"]
            color_idx = 0
            position = 0
            for block in self.highlight:
                tokens = extract_tokens(block)
                if len(tokens) > 0:
                    left = tokens[0].col - 1
                    right = tokens[-1].col - 1 + len(tokens[-1].txt)
                    print(" " * (left-position), end='')
                    print(colors[color_idx]+"^", end='')
                    print("~"*(right-left-1), end='')
                    print("\x1B[39m", end='')
                    color_idx = (color_idx + 1) % len(colors)
                    position += right-position
            print()


################################################################################


def index_token(ln, val, cls):
    idx = 0
    while idx < len(ln):
        obj = ln[idx]
        if isinstance(obj, Token):
            setlike_cls = isinstance(cls, (set, list))
            if obj.cls == cls or (setlike_cls and obj.cls in cls):
                setlike_val = isinstance(val, (set, list))
                if obj.val == val or (setlike_val and obj.val in val):
                    return idx
        idx += 1
    return None


def rindex_token(ln, val, cls):
    idx = len(ln)-1
    while idx >= 0:
        obj = ln[idx]
        if isinstance(obj, Token):
            setlike_cls = isinstance(cls, (set, list))
            if obj.cls == cls or (setlike_cls and obj.cls in cls):
                setlike_val = isinstance(val, (set, list))
                if obj.val == val or (setlike_val and obj.val in val):
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


# These are acceptable arguments to operators and built-ins.
#
AcceptableTokens = {'natural', 'string', 'name', 'keyword'}


# Arranged from high to low precedence.
#   Each element looks like [op, 'left'|'right', kind]     for binary ops
#                       and [op, 'prefix'|'postfix', kind] for unary ops
#
Operators = [['$', 'prefix', 'factory'],
             ['_', 'prefix', 'flatten'],
             ['~', 'left',   'zip'    ],
             ['*', 'left',   'star'   ],
             ['+', 'left',   'concat' ]]

Input  = {'get', 'getNum', 'getStr'}
Output = {'print', 'printNum', 'printStr', 'printRepr'}

# Returns None, an instance of ParseTree, or an instance of ParseError.
#
def _parse(line, statement=False):

    if len(line) == 0:
        return None

    while (lp := index_token(line, "(", 'delimiter')) is not None:
        rp = index_token(line, ")", 'delimiter')
        if (rp is not None) and rp < lp:
            return ParseError("missing left parenthesis", line[rp])
        height = 1
        rp = lp + 1
        while True:
            if rp >= len(line):
                return ParseError("missing right parenthesis", line[lp])
            obj = line[rp]
            if isinstance(obj, Token) and obj.cls == 'delimiter':
                if obj.val == '(': height += 1
                if obj.val == ')': height -= 1
            if height == 0: break
            rp += 1

        interior = _parse(line[lp+1:rp])
        if interior is None:
            return ParseError("nothing to parse inside parentheses", line[lp:rp+1])
        if isinstance(interior, ParseError):
            return interior

        line = line[:lp] + [interior] + line[rp+1:]

    # And now, at this point, we're guaranteed that aren't any parentheses.
    # First, construct queue literals.

    while (lb := index_token(line, "[", 'delimiter')) is not None:
        if DEBUG:
            print("\x1B[2m"+str(len(line)).rjust(2)+"\x1B[22m", end="\x1B[G")
            print("\x1B[" + str(line[lb].col+3) + "C1", end="\x1B[G")
        rb = index_token(line, "]", 'delimiter')
        if (rb is not None) and rb < lb:
            return ParseError("missing left bracket", line[rb])

        elems = []
        current_elem = []
        height = 1
        rb = lb + 1
        while True:
            if rb >= len(line):
                if DEBUG:
                    print()
                return ParseError("missing right bracket", line[lb])
            obj = line[rb]
            if height == 1 and isinstance(obj, Token) and obj.cls == 'separator' and obj.val == ',':
                elems.append(current_elem)
                current_elem = []
            else:
                if isinstance(obj, Token) and obj.cls == 'delimiter':
                    if obj.val == '[': height += 1
                    if obj.val == ']': height -= 1
                    if DEBUG:
                        print("\x1B[" + str(obj.col+3) + "C" + str(height), end="\x1B[G")
                if height == 0: break
                current_elem.append(obj)
            rb += 1

        elems.append(current_elem)

        if DEBUG:
            print()
            print("\x1B[" + str(line[lb].col+3) + "C[", end="\x1B[G")
            print("\x1B[" + str(line[rb].col+3) + "C]", end="\x1B[G")

        interior = []
        if DEBUG:
            for elem in elems:
                if len(elem) > 0:
                    print("\x1B[" + str(elem[0].col+3) + "C^", end="\x1B[G")
            print()
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
                idx = interior.index(None)
                return ParseError("extraneous delimiter", line[lb+1:rb])

        literal = ParseTree('literal', interior)
        line = line[:lb] + [literal] + line[rb+1:]

    # At this point, we're guaranteed that aren't any parentheses or brackets.
    # Second, complain about any braces, since they don't do anything yet.

    if (idx := index_token(line, "{", 'delimiter') is not None) \
            or (idx := index_token(line, "}", 'delimiter') is not None):
        return ParseError("illegal delimiter", line[idx])

    # Third, parse operators and application (concatenation).
    for op, assoc, kind in Operators:
        if assoc in ['left', 'right']:
            while True:
                if assoc == 'left':
                    idx = index_token(line, op, 'operator')
                if assoc == 'right':
                    idx = rindex_token(line, op, 'operator')
                if idx is None:
                    break
                if idx == 0:
                    return ParseError(f"binary operator {op} missing left argument", line[idx])
                if idx == len(line)-1:
                    return ParseError(f"binary operator {op} missing right argument", line[idx])
                lhs = line[idx-1]
                rhs = line[idx+1]
                if isinstance(lhs, Token) and lhs.cls not in AcceptableTokens:
                    return ParseError(f"invalid left argument for binary operator {op}", lhs)
                if isinstance(rhs, Token) and rhs.cls not in AcceptableTokens:
                    return ParseError(f"invalid right argument for binary operator {op}", rhs)
                tree = ParseTree(kind, [lhs, rhs])
                line = line[:idx-1] + [tree] + line[idx+2:]

        if assoc in ['prefix', 'postfix']:
            while True:
                if assoc == 'postfix':
                    idx = index_token(line, op, 'operator')
                if assoc == 'prefix':
                    idx = rindex_token(line, op, 'operator')
                if idx is None:
                    break
                if idx == 0 and assoc == 'postfix':
                    return ParseError(f"postfix operator {op} missing argument", line[idx])
                if idx == len(line)-1 and assoc == 'prefix':
                    return ParseError(f"prefix operator {op} missing argument", line[idx])
                if assoc == 'postfix':
                    arg = line[idx-1]
                if assoc == 'prefix':
                    arg = line[idx+1]
                if isinstance(arg, Token) and arg.cls not in AcceptableTokens:
                    return ParseError(f"invalid argument for {assoc} operator {op}", arg)
                tree = ParseTree(kind, [arg])
                if assoc == 'postfix':
                    line = line[:idx-1] + [tree] + line[idx+1:]
                if assoc == 'prefix':
                    line = line[:idx] + [tree] + line[idx+2:]

    # Only ParseTrees and natural, string, keyword, name, and ":=" tokens should
    #   be left. Newlines, delimiters, specials, separators, and operators other
    #   than ":=" are illegal at this point.
    # TODO

    # And we're all done!
    if len(line) < 1:
        raise Exception("this should never happen")

    # ...unless this is a statement.
    if statement:
        # Statments look like one of
        #   <name> := <tree|token>      # assignment
        #   <output> <tree|token>       # output
        #   <tree|token>                # implicit print
        if len(line) == 1:
            okay = not (isinstance(line[0], Token) and line[0].val in Output)
            if okay:
                return line[0]

        if len(line) == 2:
            okay = isinstance(line[0], Token) and line[0].val in Output and \
                   not (isinstance(line[1], Token) and line[1].val in Output)
            if okay:
                return ParseTree('output', line)

        if len(line) == 3:
            okay = isinstance(line[0], Token) and line[0].cls == 'name' and \
                   isinstance(line[1], Token) and line[1].val == ':='
            if okay:
                return ParseTree('assignment', line[0::2])

        return ParseError("not a statement or reducible expression", line, True)

    # And if it's not a statement...
    if len(line) > 1:
        return ParseError("undreducible expression", line, True)
    else:
        return line[0]


def parse_line(stream):
    # read until we encounter a newline
    line = []
    while True:
        tok = next(stream)
        if (tok is None) or (tok.cls == 'newline'):
            break
        line.append(tok)

    return _parse(line, True)


################################################################################


if __name__ == "__main__":

    from sys import exit

    def prompt():
        print("\x1B[2mparse>\x1B[22m ", end='')
        line = input()
        if line in ['exit', 'quit']:
            exit()
        return line + "\n"

    stream = TokenStream("", prompt)

    try:
        while True:
            ln = parse_line(stream)
            if isinstance(ln, ParseError):
                ln.display(stream.log)
            else:
                print(ln)

    except KeyboardInterrupt:
        print("\b\bexit")

    except EOFError:
        print('exit')

