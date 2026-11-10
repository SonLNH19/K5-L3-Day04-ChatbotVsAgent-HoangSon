"""Kiểm tra định tuyến API bằng client giả, không gửi key hoặc gọi mạng."""
import unittest
from unittest.mock import patch

import agent


class ProviderTests(unittest.TestCase):
    def test_openrouter_uses_bearer_token_and_correct_endpoint(self):
        with patch.dict(agent.os.environ, {"OPENROUTER_API_KEY": "test-router-key"}, clear=True), \
             patch.object(agent, "PROVIDER", "openrouter"), \
             patch.object(agent, "MODEL", "anthropic/claude-haiku-5.5"), \
             patch.object(agent, "_client", None), \
             patch.object(agent.anthropic, "Anthropic") as factory:
            messages = [{"role": "user", "content": "Xin chào"}]
            result = agent.call_model(messages)
            factory.assert_called_once_with(
                auth_token="test-router-key", base_url="https://openrouter.ai/api",
                timeout=60.0, max_retries=1,
            )
            factory.return_value.messages.create.assert_called_once_with(
                model="anthropic/claude-haiku-5.5", max_tokens=4000,
                system=agent.SYSTEM_PROMPT, tools=agent.TOOLS, messages=messages,
            )
            self.assertIs(result, factory.return_value.messages.create.return_value)
            agent.call_model(messages)
            self.assertEqual(factory.call_count, 1)

    def test_anthropic_uses_its_own_key(self):
        with patch.dict(agent.os.environ, {"ANTHROPIC_API_KEY": "test-anthropic-key"}, clear=True), \
             patch.object(agent, "PROVIDER", "anthropic"), \
             patch.object(agent, "_client", None), \
             patch.object(agent.anthropic, "Anthropic") as factory:
            agent.call_model([])
            factory.assert_called_once_with(api_key="test-anthropic-key", timeout=60.0, max_retries=1)

    def test_missing_key_does_not_create_client(self):
        for key in ("", "sk-or-..."):
            with self.subTest(key=key), \
                 patch.dict(agent.os.environ, {"OPENROUTER_API_KEY": key}, clear=True), \
                 patch.object(agent, "PROVIDER", "openrouter"), \
                 patch.object(agent, "_client", None), \
                 patch.object(agent.anthropic, "Anthropic") as factory:
                with self.assertRaisesRegex(SystemExit, "OPENROUTER_API_KEY"):
                    agent.call_model([])
                factory.assert_not_called()

    def test_unknown_provider_does_not_create_client(self):
        with patch.object(agent, "PROVIDER", "unknown"), \
             patch.object(agent, "_client", None), \
             patch.object(agent.anthropic, "Anthropic") as factory:
            with self.assertRaisesRegex(SystemExit, "LLM_PROVIDER"):
                agent.call_model([])
            factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
