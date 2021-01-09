test_counter = 0
succeeded = 0


def test(name, assertion):
    global test_counter
    global succeeded
    if assertion:
        fmt = "[\x1B[38;5;42mpass\x1B[39m]  %2d: %s"
        succeeded += 1
    else:
        fmt = "[\x1B[38;5;203mfail\x1B[39m]  %2d: %s"
    print(fmt % (test_counter, name))
    test_counter += 1


def note(msg):
    print("[\x1B[38;5;105mnote\x1B[39m]  %s" % msg)


def summary():
    global test_counter
    global succeeded
    if succeeded == test_counter:
        print("[\x1B[38;5;42mokay\x1B[39m]  all tests passed!")
    else:
        failed = test_counter - succeeded
        if failed == 1:
            msg = " 1 test failed"
        else:
            msg = "%2d tests failed" % failed
        print("[\x1B[38;5;203mohno\x1B[39m]  " + msg)
