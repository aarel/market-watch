from scripts.dev_tools_tui import _parse_pytest_status_line


def test_parse_pytest_status_line_recognizes_status():
    line = "tests/test_sample.py::test_example PASSED"
    assert _parse_pytest_status_line(line) == "tests/test_sample.py::test_example"


def test_parse_pytest_status_line_handles_class():
    line = "tests/test_sample.py::TestFoo::test_bar FAILED"
    assert _parse_pytest_status_line(line) == "tests/test_sample.py::TestFoo::test_bar"


def test_parse_pytest_status_line_ignores_other_output():
    assert _parse_pytest_status_line("collected 10 items") is None
