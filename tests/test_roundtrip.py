import sys, pathlib
import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import scrambler_sim as s


@pytest.fixture(scope="module")
def img():
    return np.random.default_rng(0).integers(0, 255, (s.H, s.W, 3), dtype=np.uint8)


@pytest.mark.parametrize("mode", ["syster", "videocrypt"])
@pytest.mark.parametrize("std", ["pal", "secam"])
@pytest.mark.parametrize("safe", [True, False])
def test_roundtrip(img, mode, std, safe):
    sc = s.Scrambler(mode, std, 42, chroma_safe=safe)
    for n in range(3):
        enc = sc.encode(img, n)
        assert not np.array_equal(enc, img)
        assert np.array_equal(sc.decode(enc, n), img)


def test_wrong_key_does_not_decode(img):
    a = s.Scrambler("syster", "pal", 1)
    b = s.Scrambler("syster", "pal", 2)
    assert not np.array_equal(b.decode(a.encode(img, 0), 0), img)


def test_syster_preserves_field_parity(img):
    sc = s.Scrambler("syster", "secam", 7, chroma_safe=True)
    perm = sc.syster_perm(0)
    assert np.all((perm - np.arange(s.H)) % 2 == 0)


def test_pal_safe_has_lower_phase_error():
    safe = s.Scrambler("videocrypt", "pal", 5, chroma_safe=True)
    unsafe = s.Scrambler("videocrypt", "pal", 5, chroma_safe=False)
    e_safe = np.abs(s.pal_phase_error_shift(safe.cuts)).mean()
    e_unsafe = np.abs(s.pal_phase_error_shift(unsafe.cuts)).mean()
    assert e_safe < e_unsafe
