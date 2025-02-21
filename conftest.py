#!/usr/bin/env python
import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner


def pytest_configure():
    os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings"
    django.setup()


def run(path):
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(path)
    sys.exit(bool(failures))


if __name__ == "__main__":
    run(sys.argv[1:])
