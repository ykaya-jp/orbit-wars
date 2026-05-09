"""Smoke tests — verify orbit_wars imports."""


def test_import_package():
    import orbit_wars as pkg

    assert pkg.__version__
