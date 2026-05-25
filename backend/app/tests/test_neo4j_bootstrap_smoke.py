import os
import unittest

from core.config import settings
from graph.bootstrap import SCHEMA_VERSION, bootstrap_neo4j


class Neo4jBootstrapSmokeTests(unittest.TestCase):
    def test_bootstrap_applies_migrations_when_neo4j_available(self):
        if os.environ.get("SKIP_NEO4J_SMOKE") == "1":
            self.skipTest("Neo4j smoke test skipped by SKIP_NEO4J_SMOKE")

        try:
            from neo4j import GraphDatabase
        except ImportError:
            self.skipTest("neo4j driver not installed")

        uri = os.environ.get("NEO4J_URI", settings.NEO4J_URI)
        user = os.environ.get("NEO4J_USER", settings.NEO4J_USER)
        password = os.environ.get("NEO4J_PASSWORD", settings.NEO4J_PASSWORD)

        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            driver.verify_connectivity()
        except Exception as exc:
            self.skipTest(f"Neo4j not reachable at {uri}: {exc}")

        try:
            result = bootstrap_neo4j(driver)
            self.assertEqual(result["target_version"], SCHEMA_VERSION)
            self.assertGreaterEqual(result["schema_version"], 1)
            self.assertIn(result["status"], {"bootstrapped", "ok"})
        finally:
            driver.close()


if __name__ == "__main__":
    unittest.main()
