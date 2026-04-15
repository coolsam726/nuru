def test_package_imports():
    import importlib
    # Ensure the package imports without error
    mod = importlib.import_module('nuru')
    assert mod is not None
