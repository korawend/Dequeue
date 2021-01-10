import pytest
from typing import List
from copy import deepcopy

from queuen.parser import ParseTree
from queuen.lexer import Token

class Generator:
    def __init__(self):
        self.refresh()

    def refresh(self):
        pass

def literal(lst: List):
    lst = deepcopy(lst)
    class Literal(Generator):
        def copy(self):
            return literal(lst)

        def refresh(self):
            self.at = 0

        def next(self):
            if self.at < len(lst):
                v = lst[self.at]
                self.at += 1
                return v
            raise StopIteration
    return Literal()

def const(i: int):
    class Const(Generator):
        def copy(self):
            return const(i)

        def refresh(self):
            self.at = 0

        def next(self):
            if self.at < i:
                self.at += 1
                return []
            raise StopIteration
    return Const()

def factory(it):
    class Factory(Generator):
        def copy(self):
            return factory(it)

        def next(self):
            return it.copy()

    return Factory()

def concat(it1, it2):
    it1 = it1.copy()
    it2 = it2.copy()

    class Concat(Generator):
        def copy(self):
            return concat(it1.copy(), it2.copy())

        def next(self):
            try:
                return it1.next()
            except StopIteration:
                return it2.next()
    return Concat()

stdzip = zip
def zip(it1, it2):
    it1 = it1.copy()
    it2 = it2.copy()

    class Zip(Generator):
        def copy(self):
            return zip(it1.copy(), it2.copy())

        def next(self):
            lhs = it1.next()
            rhs = it2.next()
            return concat(lhs, rhs)
    return Zip()

def take(n):
    def f(it):
        return [it.next() for _ in range(n)]
    return f

take1 = take(1)
take2 = take(2)
take3 = take(3)

zero = []
one = [[]]
two = [[], []]
three = [[], [], []]
four = [[], [], [], []]
five = [[], [], [], [], []]

class TestEval:
    def _test(self, it, n, expect):
        if expect is StopIteration:
            with pytest.raises(StopIteration):
                take(n)(it)
        else:
            assert take(n)(it) == expect

    def test_pass(self):
        pass

    @pytest.mark.parametrize("n, expect", [
        (1, [[]]),
        (2, [[], []]),
        (3, [[], [], []]),
        (4, [[], [], [], []]),
        (5, [[], [], [], [], []]),
    ])
    def test_const(self, n, expect):
        it = const(7)
        self._test(it, n, expect)

    @pytest.mark.parametrize("n, expect", [
        (1, [[]]),
        (2, [[], []]),
        (3, StopIteration),
    ])
    def test_const_2(self, n, expect):
        it = const(2)
        self._test(it, n, expect)

    def test_factory(self):
        it1 = const(2)
        it = factory(it1)

        # test that next($2) is 2
        for _ in range(100):
            n = it.next()
            self._test(n, 2, two)

        # test that next($2) has 2 items
        for _ in range(100):
            n = it.next()
            self._test(n, 3, StopIteration)

    def test_concat(self):
        it1 = const(2)
        it2 = const(3)
        it = concat(it1, it2)
        self._test(it, 5, five)

    def test_concat_factory(self):
        it1 = const(2)
        it2 = const(3)
        it_c = concat(it1, it2)
        it = factory(it_c)

        for _ in range(100):
            n = it.next()
            self._test(n, 5, five)

        for _ in range(100):
            n = it.next()
            self._test(n, 6, StopIteration)

    def test_literal(self):
        it = literal([1, 2, 3])
        self._test(it, 3, [1, 2, 3])

    def test_literal_concat(self):
        it1 = literal([1, 2, 3])
        it2 = literal([4, 5, 6])
        it = concat(it1, it2)
        self._test(it, 6, [1, 2, 3, 4, 5, 6])

    def test_literal_factory(self):
        it1 = literal([1, 2, 3])
        it = factory(it1)

        for _ in range(100):
            n = it.next()
            self._test(n, 3, [1, 2, 3])

    def test_literal_concat_factory(self):
        it1 = literal([1, 2, 3])
        it2 = literal([4, 5, 6])
        it = factory(concat(it1, it2))

        for _ in range(100):
            n = it.next()
            self._test(n, 3, [1, 2, 3])

        for _ in range(100):
            n = it.next()
            self._test(n, 6, [1, 2, 3, 4, 5, 6])

        for _ in range(100):
            n = it.next()
            self._test(n, 7, StopIteration)

    def test_literal_factory_zip(self):
        it1 = factory(literal([1, 2, 3]))
        it2 = factory(literal([4, 5, 6]))
        it = zip(it1, it2)

        for _ in range(100):
            n = it.next()
            self._test(n, 3, [1, 2, 3])

        for _ in range(100):
            n = it.next()
            self._test(n, 6, [1, 2, 3, 4, 5, 6])

        for _ in range(100):
            n = it.next()
            self._test(n, 7, StopIteration)

