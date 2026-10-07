import unittest
import uuid
import base64
import yaml
import json
from app.database import db
from app.services.repository import repo
from app.subscriptions.engine import subscription_engine

class TestSubscription(unittest.TestCase):
    def setUp(self):
        db.init_schema()
        uname = f"sub_user_{uuid.uuid4().hex[:8]}"
        self.user = repo.create_user(uname, "Subscription Tester")
        self.node1 = repo.create_node(
            name="miliconfig-01 • US Premium",
            protocol="vless",
            address="us.miliconfig.com",
            port=443,
            region="US"
        )
        self.node2 = repo.create_node(
            name="miliconfig-02 • DE Fast",
            protocol="trojan",
            address="de.miliconfig.com",
            port=443,
            region="DE"
        )

    def test_client_node_naming_enforcement(self):
        """Strict rule: all client-facing node names must start with 'miliconfig'."""
        name1 = subscription_engine.format_client_node_name("TestNode", 1, "US", "VLESS")
        self.assertTrue(name1.startswith("miliconfig"))
        
        name2 = subscription_engine.format_client_node_name("miliconfig-05", 5, "DE", "Trojan")
        self.assertTrue(name2.startswith("miliconfig"))

    def test_base64_subscription(self):
        status, content, ctype = subscription_engine.build_subscription(
            token=self.user.subscription_token,
            target_param="base64"
        )
        self.assertEqual(status, 200)
        self.assertEqual(ctype, "text/plain; charset=utf-8")
        decoded = base64.b64decode(content).decode("utf-8")
        self.assertIn("vless://", decoded)
        self.assertIn("trojan://", decoded)
        self.assertIn("miliconfig", decoded)

    def test_clash_subscription(self):
        status, content, ctype = subscription_engine.build_subscription(
            token=self.user.subscription_token,
            target_param="clash"
        )
        self.assertEqual(status, 200)
        self.assertEqual(ctype, "text/yaml; charset=utf-8")
        config = yaml.safe_load(content)
        self.assertIn("proxies", config)
        self.assertIn("proxy-groups", config)
        for proxy in config["proxies"]:
            self.assertTrue(proxy["name"].startswith("miliconfig"), f"Node name violation: {proxy['name']}")

    def test_singbox_subscription(self):
        status, content, ctype = subscription_engine.build_subscription(
            token=self.user.subscription_token,
            target_param="singbox"
        )
        self.assertEqual(status, 200)
        self.assertEqual(ctype, "application/json; charset=utf-8")
        config = json.loads(content)
        self.assertIn("outbounds", config)
        nodes_found = [ob for ob in config["outbounds"] if ob.get("tag", "").startswith("miliconfig")]
        self.assertTrue(len(nodes_found) > 0)

    def test_user_agent_detection(self):
        self.assertEqual(subscription_engine.detect_client_format("ClashMeta/v1.16.0"), "clash")
        self.assertEqual(subscription_engine.detect_client_format("Mihomo/1.18.0"), "clash")
        self.assertEqual(subscription_engine.detect_client_format("sing-box/1.12.0"), "singbox")
        self.assertEqual(subscription_engine.detect_client_format("v2rayng/1.8.5"), "base64")
        self.assertEqual(subscription_engine.detect_client_format("Mozilla/5.0"), "base64")

if __name__ == "__main__":
    unittest.main()
