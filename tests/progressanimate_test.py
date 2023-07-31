from time import sleep

import pytest

import pysimplesql as ss

# ruff: noqa


# Simulated process
def process(raise_error=False):
    if raise_error:
        raise ValueError("Oops! This process had an error!")
    sleep(5)


def test_successful_process() -> None:
    try:
        sa = ss.ProgressAnimate("Test ProgressAnimate")
        sa.run(process, False)
    except Exception as e:
        assert False, f"An exception was raised: {e}"


def test_exception_during_process() -> None:
    with pytest.raises(Exception):
        sa = ss.ProgressAnimate("Test ProgressAnimate")
        v = sa.run(process, True)
        print(v, type(v))


def test_config() -> None:
    # What if config was set with an int?
    with pytest.raises(ValueError):
        ss.ProgressAnimate("Test", config=1)
    # What if config was set with a string
    with pytest.raises(ValueError):
        ss.ProgressAnimate("Test", config="My Config")
    # What if config was set with a list?
    with pytest.raises(ValueError):
        ss.ProgressAnimate("Test", config=["red"])
    # What if config was set with a bool?
    with pytest.raises(ValueError):
        ss.ProgressAnimate("Test", config=True)
    # What if the user does supply a dict, but it doesn't have the right keys?
    with pytest.raises(NotImplementedError):
        # Purposely fail by using unsupported key
        config = {
            "sound_effect": "beep",
        }
        ss.ProgressAnimate("Test", config=config)
    # What if supplies a correct key, but does not have required subdict keys?
    with pytest.raises(ValueError):
        # purposely omit the offset
        config = {
            "red": {"value_start": 0, "value_range": 100, "period": 2},
        }
        ss.ProgressAnimate("Test", config=config)
    # What if the user does supply a dict, but it doesn't have the right values?
    with pytest.raises(ValueError):
        # Purposely fail by using unsupported value
        config = {
            "red": {"value_start": True, "value_range": "A", "period": 2, "offset": 0},
            "phrases": [True, 0, 3.14, "This one is good though"],
        }
        ss.ProgressAnimate("Test", config=config)


def test_run() -> None:
    with pytest.raises(ValueError):
        pa = ss.ProgressAnimate("Test")
        pa.run(True)
