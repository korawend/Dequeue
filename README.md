# DQ: *The* Queue-Based Programming Language

_Winner of the "The Knuth Award" and "Turbo" awards from [Quirky Languages Done
 Quick](https://quirkylanguages.com/)!_


MULTIPLICATION

  Multiplication `a*b` is absolutely nothing more than syntactic sugar for
  `_(b~$a)`.

  [explanation and example of natural number multiplication]

  By happy coincidence, multiplication between string and natural numbers works
  the obvious way:

    "Hello" * 2   =>   "HelloHello"

    2 * "Hello"   =>   510


ERRORS

  Error messages are usually very helpful and sometimes very misleading.

  The only errors are parse errors; it's (supposed to be) impossible to cause an
  evaluation error.

  For example, the interpreter is perfectly happy to let you reference a name
  that's not been defined.

    printRepr wat   =>   ε



Table of Contents

Premise
Number and string representations
Addition
The other operations
Multiplication
The details of smart printing
Other ways of printing
Assignment  (x := 4 \n x+x => 4 \n you should use factories)
Errors
