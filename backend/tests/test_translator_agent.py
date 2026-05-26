from backend.src.agents.tool_agents.translator_agent import TranslatorAgent


def make_agent() -> TranslatorAgent:
    return TranslatorAgent(
        config={
            "update_term": "False",
            "llm_config": {"model": "gpt-4.1", "base_url": "http://example.com", "api_key": "test"},
            "target_language": "ch",
            "source_language": "en",
            "category": {},
            "user_term": "",
        },
        project_dir="/tmp/project",
        output_dir="/tmp/output",
    )


def test_extract_message_text_handles_responses_content_parts() -> None:
    agent = make_agent()

    content = [
        {
            "type": "text",
            "text": "\\section{引言}",
            "annotations": [],
            "id": None,
        }
    ]

    assert agent._extract_message_text(content) == "\\section{引言}"


def test_extract_message_text_handles_plain_string() -> None:
    agent = make_agent()

    assert agent._extract_message_text("plain translation") == "plain translation"
