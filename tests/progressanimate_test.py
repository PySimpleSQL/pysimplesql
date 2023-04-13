from time import sleep

import pytest

import pysimplesql as ss


# Simulated process
def process(raise_error=False):
    if raise_error:
        raise ValueError("Oops! This process had an error!")
    sleep(5)


def test_successful_process():
    try:
        sa = ss.ProgressAnimate("Test ProgressAnimate")
        sa.run(process, False)
    except Exception as e:
        assert False, f"An exception was raised: {e}"


def test_exception_during_process():
    with pytest.raises(Exception):
        sa = ss.ProgressAnimate("Test ProgressAnimate")
        v = sa.run(process, True)
        print(v, type(v))


def test_config():
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
        # Purposely fail by
        config = {
            "sound_effect": "beep",
        }
        ss.ProgressAnimate("Test", config=config)
