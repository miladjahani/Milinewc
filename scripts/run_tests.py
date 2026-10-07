import os
import sys
import unittest
import importlib.util

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Ensure app package is registered in sys.modules
if "app" not in sys.modules:
    app_dir = os.path.join(root_dir, "app")
    spec = importlib.util.spec_from_file_location("app", os.path.join(app_dir, "__init__.py"), submodule_search_locations=[app_dir])
    app_mod = importlib.util.module_from_spec(spec)
    sys.modules["app"] = app_mod
    spec.loader.exec_module(app_mod)

test_files = [
    "test_auth.py",
    "test_users.py",
    "test_vless.py",
    "test_trojan.py",
    "test_shadowsocks.py",
    "test_subscription.py",
    "test_dns.py",
    "test_routing.py",
    "test_proxyip.py",
    "test_migration.py"
]

def load_tests():
    suite = unittest.TestSuite()
    tests_dir = os.path.join(root_dir, "tests")
    loader = unittest.TestLoader()

    for tf in test_files:
        path = os.path.join(tests_dir, tf)
        mod_name = f"tests.{tf[:-3]}"
        spec = importlib.util.spec_from_file_location(mod_name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
        suite.addTests(loader.loadTestsFromModule(mod))
    return suite

if __name__ == "__main__":
    suite = load_tests()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
