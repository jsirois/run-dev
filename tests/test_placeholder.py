# Copyright 2025 John Sirois.
# Licensed under the Apache License, Version 2.0 (see LICENSE).

import re
import sys

import pytest
from packaging.markers import default_environment

from dev_cmd.model import Factor
from dev_cmd.placeholder import Environment


@pytest.fixture
def env() -> Environment:
    return Environment()


def substitute(env: Environment, text: str) -> str:
    return env.substitute(text)[0]


def test_substitute_noop(env: Environment) -> None:
    assert "" == substitute(env, "")
    assert "foo" == substitute(env, "foo")


def test_substitute_env() -> None:
    env = Environment(env={"FOO": "bar", "BAZ": "FOO"})

    assert "bar" == substitute(env, "{env.FOO}")
    assert "FOO" == substitute(env, "{env.BAZ}")

    assert "bar" == substitute(env, "{env.{env.BAZ}}"), "Expected recursive substitution to work."

    assert "baz" == substitute(env, "{env.DNE:baz}"), "Expected defaulting to work."
    assert "env.FOO" == substitute(env, "{env.DNE:env.FOO}")

    assert "bar" == substitute(
        env, "{env.DNE:{env.also_DNE:{env.FOO}}}"
    ), "Expected recursive defaults would work."

    with pytest.raises(ValueError, match=re.escape("The environment variable 'DNE' is not set.")):
        env.substitute("{env.DNE}")


def test_substitute_markers(env) -> None:
    current_markers = default_environment()

    assert (
        ".".join(map(str, sys.version_info[:2]))
        == current_markers["python_version"]
        == substitute(env, "{markers.python_version}")
    )
    assert (
        ".".join(map(str, sys.version_info[:3]))
        == current_markers["python_full_version"]
        == substitute(env, "{markers.python_full_version}")
    )

    with pytest.raises(
        ValueError, match=re.escape("There is no Python environment marker named 'bob'.")
    ):
        env.substitute("{markers.bob}")


def test_substitute_factors(env: Environment) -> None:
    factors = Factor("a1"), Factor("b2")
    assert ("1", (Factor("a1"),)) == env.substitute("{-a}", *factors)
    assert ("2", (Factor("b2"),)) == env.substitute("{-b}", *factors)
    assert ("12", (Factor("a1"), Factor("b2"))) == env.substitute("{-a}{-b}", *factors)
    assert ("123", (Factor("a1"), Factor("b2"))) == env.substitute("{-a}{-b}{-c:3}", *factors)

    with pytest.raises(ValueError, match=re.escape("The factor parameter '-c' is not set.")):
        env.substitute("{-c}", *factors)

    with pytest.raises(
        ValueError,
        match=re.escape(
            "The factor parameter '-foo' matches more than one factor argument: '-foo1' '-foobar2'"
        ),
    ):
        env.substitute("{-foo}", Factor("foo1"), Factor("foobar2"))


def test_substitute_intra_recursive() -> None:
    expected_python_version = ".".join(map(str, sys.version_info[:2]))

    env = Environment(env={"USE_FACTOR": "py", "USE_MARKER": "python_version"})
    assert expected_python_version == substitute(env, "{markers.{env.USE_MARKER}}")
    assert (expected_python_version, (Factor("py{markers.{env.USE_MARKER}}"),)) == env.substitute(
        "{-{env.USE_FACTOR}}", Factor("py{markers.{env.USE_MARKER}}")
    )