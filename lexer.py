# Each of these can be sequence of alphabetic characters
#
KEYWORD = set()

# These must be only one character long.
#
DELIMITER = {'(', ')', '[', ']', '{', '}'}
SPECIAL   = set()
SEPARATOR = {',', ';'}

# STRING_LEFT and STRING_RIGHT may be more than one character long,
#   but the ESCAPE_CHARACTER must be only one character long.
STRING_LEFT      = '"'
STRING_RIGHT     = '"'
ESCAPE_CHARACTER = '\\'

# This may be more than one character long.
#
COMMENT = '#'

# These may be more than one character long.
#
OPERATOR = {'!',  '@',  '$',  '%',  '^',  '&',  '*',  '-',  '+',  '|',
            '!!', '@@', '$$', '%%', '^^', '&&', '**', '--', '++', '||',
            '!=', '@=', '$=', '%=', '^=', '&=', '*=', '-=', '+=', '|=',

            '<',   '>',   '.',   '=',  ':',  '?',  '/',  '\\',   '~',
            '<<',  '>>',  '..',  '==', '::', '??', '//', '\\\\',
                          '.=',        ':=', '?=', '/=', '\\=',  '~=',
            '<<<', '>>>', '...', '===',

            '/\\', '\\/', '<>', '</>', '<:', ':>', '<-<', '>->',
                                '=/=', '<~', '~>',
                                '<=>', '<|', '|>',

            '<-', '->', '=<', '>=', '=<<', '>>=', '↑',
            '←',  '→',  '<=', '=>', '<<=', '=>>', '↓',
                        '≤',  '≥',

            '×', '×=', '÷', '÷=', '⋅', '⋅=', '∘',

            '_'}

# Characters that are part of an operator but may also appear as part of a name.
#   (These must be only one character long.)
#
MID_WORD_SYMBOL = set()
END_WORD_SYMBOL = set()


    ########################################################################


WHITESPACE = {' ', '\t', '\r', '\n', '\f', '\v'}

STRING_START   = STRING_LEFT[0]
COMMENT_START  = COMMENT[0]
OPERATOR_START = set(opr[0] for opr in OPERATOR)

# Words may not contain the following characters; these will terminate a word.
#
NON_WORD = ( (DELIMITER | SPECIAL | SEPARATOR | OPERATOR_START
                        | {STRING_START, COMMENT_START}
             ) - MID_WORD_SYMBOL
           ) | END_WORD_SYMBOL | WHITESPACE

SORTED_OPERATOR = reversed(sorted(OPERATOR, key = len))

import re
ws_regex  = re.compile(r"\s+")
num_regex = re.compile(r"\d+(\.\d+)?")


################################################################################


class Token:
    def __init__(self, text, line, column, token_value, token_class):
        self.txt = text
        self.ln  = line
        self.col = column
        self.val = token_value
        self.cls = token_class

    def __eq__(self, other):
        if not isinstance(other, Token):
            return False
        return (self.val == other.val and self.cls == other.cls)

    def isexactly(self, other):
        if not isinstance(other, Token):
            return False
        return (self.txt == other.txt and \
                self.ln  == other.ln  and \
                self.col == other.col and \
                self.val == other.val and \
                self.cls == other.cls )

    def __repr__(self):
        tk = "\x1B[38;5;42mToken\x1B[39m"
        if self.val is None:
            value = "_"
        elif isinstance(self.val, str):
            value = '"' + self.val.replace("\n", "\\n") + '"'
        else:
            value = str(self.val)
        return f"⟨{tk} {value} : {self.cls} @ {self.ln},{self.col}⟩"


class TokenStream:
    # text  :=  text to be tokenized
    # more  :=  nullary function that will be called to get more text
    def __init__(self, text, more = None):
        self.text   = text
        self.more   = more
        self.line   = 1
        self.column = 1
        self.last_emitted_newline = False

    def _advance(self, string):
        newlines = string.count("\n")
        if newlines == 0:
            self.column = self.column + len(string)
        else:
            self.line = self.line + newlines
            self.column = len(string) - string.rindex("\n")

    def __next__(self): ########################################################
        while True:
            # Strip leading whitespace or return a newline #################
            match = ws_regex.match(self.text)
            if match is not None:
                whitespace, self.text = match.group(), self.text[match.end():]
                tok_line, tok_column = self.line, self.column
                self._advance(whitespace)
                if ("\n" in whitespace) and not self.last_emitted_newline:
                    self.last_emitted_newline = True
                    return Token(whitespace, tok_line, tok_column, None, 'newline')

            # Is the text empty? ###########################################
            if self.text == "":
                if self.more is None:
                    return None
                self.text += self.more()

            # Is this a comment? ###########################################
            if self.text.startswith(COMMENT):
                try:
                    end_of_comment = self.text.index("\n")
                    self.text = self.text[end_of_comment:]
                    continue
                except Exception:
                    self.text = ""
                    if self.more is None:
                        return None
                    self.text += self.more()

            ################################################################
            # At this point, we're guaranteed not to return a newline,
            #   so go ahead and preëmptively change last_emitted_newline.
            self.last_emitted_newline = False

            tok_line, tok_column = self.line, self.column

            # Is the next token an integer or decimal fraction? ############
            # TODO support 0x, 0o, and 0b notation
            match = num_regex.match(self.text)
            if match is not None:
                numstr= match.group()
                if "." in numstr:
                    num = float(numstr)
                    tok_class = 'float'
                else:
                    num = int(numstr)
                    tok_class = 'integer'
                self._advance(numstr)
                self.text = self.text[match.end():]
                return Token(numstr, tok_line, tok_column, num, tok_class)

            # Is the next token a string? ##################################
            if self.text.startswith(STRING_LEFT):
                self._advance(STRING_LEFT)
                self.text = self.text[len(STRING_LEFT):]

                idx = 0
                while True:
                    try:
                        jdx = self.text.index(STRING_RIGHT, idx)
                        if jdx > 0 and self.text[jdx-1] == ESCAPE_CHARACTER:
                            idx = jdx + 1
                        else:
                            idx = jdx
                            break
                    except Exception:
                        if self.more is None:
                            raise Exception("unterminated string")
                        self.text += self.more()
                string = self.text[:idx]
                self._advance(string+STRING_RIGHT)
                self.text = self.text[idx+len(STRING_RIGHT):]

                literal = STRING_LEFT + string + STRING_RIGHT
                string = string.replace('\\"', '"')
                # TODO support other escape sequences

                return Token(literal, tok_line, tok_column, string, 'string')

            # Is the next token a delimr, special char, sepr, or opr? ######
            value = self.text[0]
            if value in (DELIMITER | SPECIAL | SEPARATOR | OPERATOR_START):
                if value in DELIMITER:
                    tok_class = 'delimiter'
                elif value in SPECIAL:
                    tok_class = 'special'
                elif value in SEPARATOR:
                    tok_class = 'separator'
                else:
                    tok_class = 'operator'
                    for opr in SORTED_OPERATOR:
                        if self.text.startswith(opr):
                            value = opr
                            break
                self._advance(value)
                self.text = self.text[len(value):]
                return Token(value, tok_line, tok_column, value, tok_class)

            # The next token must be a name or keyword #####################
            idx = 0
            while not (idx == len(self.text) or (self.text[idx] in NON_WORD)):
                idx += 1
            idx -= 1
            while self.text[idx] in MID_WORD_SYMBOL:
                idx -=1
            idx += 1
            if idx < len(self.text) and self.text[idx] in END_WORD_SYMBOL:
                word = self.text[:idx+1]
                self._advance(word)
                self.text = self.text[idx+1:]
            else:
                word = self.text[:idx]
                self._advance(word)
                self.text = self.text[idx:]
            tok_class = ('keyword' if word in KEYWORD else 'word')
            return Token(word, tok_line, tok_column, word, tok_class)


class TokenBuffer:
    # stream  :=  text or instance of TokenStream
    # more    :=  nullary function that will be called to get more text
    def __init__(self, stream, more = None):
        if isinstance(stream, str):
            self.stream = TokenStream(stream, more)
        else:
            self.stream = stream
        self.buffer = []
        self.length = float('inf')

    def __len__(self):
        if isinstance(self.length, int):
            return self.length
        else:
            raise Exception("length unknown because buffer has not been completed")

    def __getitem__(self, idx):
        if idx < 0:
            return None
        if idx >= self.length:
            return None
        if idx >= len(self.buffer):
            for _ in range(idx - len(self.buffer) + 1):
                self.buffer.append(next(self.stream))
        return self.buffer[idx]

    def complete(self):
        while (tok := next(self.stream)) is not None:
            self.buffer.append(tok)
        self.length = len(self.buffer)


################################################################################


if __name__ == '__main__':

    from util import *
    note("starting lexer unit tests")

    # Tests go here! #######################################################
    #   These are just examples; be sure to change them if you change
    #   any of the lexer constants.

    try:
        string = "2 + 2.0"
        stream = TokenStream(string)
        output = [next(stream) for _ in range(3)]
        expected = [Token("2",   1, 1, 2,   'integer' ),
                    Token("+",   1, 3, '+', 'operator'),
                    Token("2.0", 1, 5, 2.0, 'float'   )]
        result = all(a.isexactly(b) for a,b in zip(output, expected))

    except Exception:
        result = False

    test('basic arithmetic', result)


    #try:
    #    string = "a b? c-d e-?"
    #    stream = TokenStream(string)
    #    output = [next(stream) for _ in range(6)]
    #    expected = [Token("a",   1,  1, 'a',   'word'    ),
    #                Token("b?",  1,  3, 'b?',  'word'    ),
    #                Token("c-d", 1,  6, 'c-d', 'word'    ),
    #                Token("e",   1, 10, 'e',   'word'    ),
    #                Token("-",   1, 11, '-',   'operator'),
    #                Token("?",   1, 12, '?',   'operator')]
    #    result = all(a.isexactly(b) for a,b in zip(output, expected))

    #except Exception:
    #    result = False

    #test('mid- and end-word symbols', result)


    try:
        def toks():
            yield "1"
            yield "2"
            yield "3"
        tok_gen = toks()
        def callback():
            return next(tok_gen)
        stream = TokenStream("123", callback)
        output = [next(stream) for _ in range(4)]
        expected = [Token("123", 1, 1, 123, 'integer'),
                    Token("1",   1, 4,   1, 'integer'),
                    Token("2",   1, 5,   2, 'integer'),
                    Token("3",   1, 6,   3, 'integer')]
        result = all(a.isexactly(b) for a,b in zip(output, expected))

    except Exception:
        result = False

    test('using callback', result)

    try:
        # Any run of whitespace including one or more newline
        #   characters becomes one newline token, so the
        #   the following string has 7 tokens.
        string = "a\nb\n\nc\nd"
        buf = TokenBuffer(string)
        buf.complete()
        expected = Token("c", 4, 1, 'c', 'word')
        result = (buf[4].isexactly(expected) and len(buf) == 7)

    except Exception:
        result = False

    test('newlines and buffer', result)

    ########################################################################

    summary()
