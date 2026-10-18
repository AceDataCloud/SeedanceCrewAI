"""No-bill contract, lifecycle, secrecy and tool execution tests."""

import importlib
import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from crewai.tools.tool_failure import ToolFailure
from jsonschema import Draft202012Validator

S = json.loads(Path(__file__).with_name("service.json").read_text())
module = importlib.import_module(S["module"])
base = importlib.import_module(S["module"] + "._base")
Generate = getattr(module, S["generate_class"])
Retrieve = getattr(module, S["retrieve_class"])


def reply(body, status=200):
    return httpx.Response(
        status,
        json=body,
        request=httpx.Request("POST", "https://api.acedata.cloud" + S["task_path"]),
    )


def complete():
    if S["name"] == "Seedance":
        data = {
            "status": "succeeded",
            "content": {"video_url": "https://example.com/result.mp4"},
        }
    elif S["name"] == "HappyHorse":
        data = [{"state": "succeeded", "video_url": "https://example.com/result.mp4"}]
    elif S["name"] == "GPT Image":
        data = [{"url": "https://example.com/result.png"}]
    else:
        data = [
            {"image_url": "https://example.com/result.png", "prompt": "private input"}
        ]
    return {
        "id": "existing",
        "finished_at": 1,
        "request": {"key": "private request"},
        "application_id": "private app",
        "response": {
            "success": True,
            "data": data,
            "cost": {"amount": 0.1, "currency": "credit", "internal": "private cost"},
        },
    }


def test_single_submit_is_pending_and_cannot_repeat_same_instance():
    tool = Generate(api_key="secret-fixture")
    with patch(
        "httpx.Client.post", return_value=reply({"success": True, "task_id": "new"})
    ) as post:
        result = json.loads(tool.run(**S["example_input"]))
        assert (
            result["status"] == "pending"
            and not result["success"]
            and result["media_urls"] == []
        )
        assert result["task_id"] == "new"
        assert post.call_count == 1
        assert (
            post.call_args.args[0] == "https://api.acedata.cloud" + S["generation_path"]
        )
        payload = post.call_args.kwargs["json"]
        assert payload["async"] is True and payload["model"] == S["example_model"]
        if S["name"] == "Seedance":
            assert (
                payload["content"] == S["example_input"]["content"]
                and "prompt" not in payload
            )
        if S["name"] == "GPT Image":
            assert (
                payload["response_format"] == "url"
                and payload["n"] == 1
                and "count" not in payload
            )
        if S["name"] == "Nano Banana":
            assert (
                payload["count"] == 1
                and "n" not in payload
                and payload["action"] == "generate"
            )
        assert isinstance(tool.run(**S["example_input"]), ToolFailure)
        assert post.call_count == 1


def test_read_exact_service_media_shape_and_remove_private_data():
    tool = Retrieve(api_key="secret-fixture")
    with patch("httpx.Client.post", return_value=reply(complete())) as post:
        result = json.loads(tool.run(task_id="existing"))
    assert (
        result["success"]
        and result["status"] == "succeeded"
        and len(result["media_urls"]) == 1
    )
    assert post.call_args.args[0] == "https://api.acedata.cloud" + S["task_path"]
    assert post.call_args.kwargs["json"] == {"action": "retrieve", "id": "existing"}
    assert "private" not in str(result) and "secret-fixture" not in str(
        tool.model_dump()
    )


def test_unfinished_preview_never_counts_as_success():
    b = complete()
    b["finished_at"] = None
    with patch("httpx.Client.post", return_value=reply(b)):
        result = json.loads(Retrieve(api_key="key").run(task_id="existing"))
    assert result["status"] == "pending" and not result["media_urls"]


@pytest.mark.parametrize("location", ["response", "data", "top"])
def test_terminal_error_cannot_become_success(location):
    b = complete()
    if location == "response":
        b["response"]["success"] = False
    elif location == "top":
        b["state"] = "failed"
    else:
        b["response"]["data"] = {"status": "failed", "error": "private diagnostic"}
    with patch("httpx.Client.post", return_value=reply(b)):
        result = Retrieve(api_key="key").run(task_id="existing")
    assert isinstance(result, ToolFailure) and not result.retryable
    assert "private diagnostic" not in str(result)


def test_terminal_without_media_is_failure_not_fake_success():
    b = complete()
    b["response"]["data"] = {}
    with patch("httpx.Client.post", return_value=reply(b)):
        result = Retrieve(api_key="key").run(task_id="existing")
    assert isinstance(result, ToolFailure) and result.code == "missing_terminal_media"


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_error_meaning_and_no_retry_or_sensitive_body(status):
    with patch(
        "httpx.Client.post",
        return_value=reply(
            {"error": "secret-fixture private upstream diagnostic"}, status
        ),
    ) as post:
        with pytest.raises(base.ServiceHTTPError) as caught:
            Generate(api_key="secret-fixture").run(**S["example_input"])
    assert caught.value.status_code == status and post.call_count == 1
    assert "secret-fixture" not in str(
        caught.value
    ) and "upstream diagnostic" not in str(caught.value)


def test_timeout_is_unknown_outcome_not_retried():
    with patch(
        "httpx.Client.post", side_effect=httpx.ReadTimeout("secret-fixture")
    ) as post:
        with pytest.raises(TimeoutError) as caught:
            Generate(api_key="secret-fixture").run(**S["example_input"])
    assert "secret-fixture" not in str(caught.value) and post.call_count == 1


def test_polling_only_reads_original_id():
    with (
        patch(
            "httpx.Client.post",
            side_effect=[
                reply({"id": "existing", "finished_at": None}),
                reply(complete()),
            ],
        ) as post,
        patch(S["module"] + "._base.time.monotonic", side_effect=[0, 1, 2]),
        patch(S["module"] + "._base.time.sleep"),
    ):
        result = json.loads(
            Retrieve(api_key="key").run(task_id="existing", wait_seconds=10)
        )
    assert result["success"] and post.call_count == 2
    assert all(
        c.args[0].endswith(S["task_path"]) and c.kwargs["json"]["id"] == "existing"
        for c in post.call_args_list
    )


def test_identity_wait_and_token_guards(monkeypatch):
    with patch("httpx.Client.post", return_value=reply(complete())):
        with pytest.raises(ValueError, match="does not match"):
            Retrieve(api_key="key").run(task_id="other")
    with pytest.raises(ValueError):
        Retrieve(api_key="key").run(task_id="existing", wait_seconds=241)
    for key in ["Bearer key", "platform-management", " key"]:
        with pytest.raises(ValueError):
            Retrieve(api_key=key)
    monkeypatch.delenv("ACEDATACLOUD_API_KEY", raising=False)
    with pytest.raises(ValueError):
        Retrieve()


def test_service_specific_input_differences_fail_before_network():
    bad = dict(S["example_input"])
    if S["name"] == "Seedance":
        bad["content"] = [{"type": "image_url", "text": "wrong shape"}]
    elif S["name"] == "HappyHorse":
        bad.update(action="image_to_video")
    elif S["name"] == "GPT Image":
        bad.update(n=0)
    else:
        bad.update(action="edit", image_urls=[])
    with patch("httpx.Client.post") as post:
        with pytest.raises(ValueError):
            Generate(api_key="key").run(**bad)
    post.assert_not_called()


def test_valid_service_options_preserved():
    values = deepcopy(S["example_input"])
    if S["name"] == "Seedance":
        values["content"].append(
            {
                "type": "image_url",
                "image_url": {"url": "https://example.com/reference.png"},
                "role": "first_frame",
            }
        )
    elif S["name"] == "HappyHorse":
        values.update(
            action="image_to_video", image_url="https://example.com/reference.png"
        )
    elif S["name"] == "GPT Image":
        values.update(background="transparent", output_format="png")
    else:
        values.update(action="edit", image_urls=["https://example.com/reference.png"])
    with patch("httpx.Client.post", return_value=reply({"task_id": "new"})) as post:
        Generate(api_key="key").run(**values)
    payload = post.call_args.kwargs["json"]
    for key, value in values.items():
        assert payload[key] == value


def test_unknown_cross_service_fields_are_rejected():
    values = dict(S["example_input"], not_a_service_field=True)
    with patch("httpx.Client.post") as post:
        with pytest.raises(ValueError):
            Generate(api_key="key").run(**values)
    post.assert_not_called()


def test_generation_payload_matches_the_pinned_public_contract():
    contract = json.loads(Path(__file__).with_name("contract-source.json").read_text())
    with patch("httpx.Client.post", return_value=reply({"task_id": "new"})) as post:
        Generate(api_key="key").run(**S["example_input"])
    Draft202012Validator(contract["generation"]).validate(post.call_args.kwargs["json"])
    assert (
        post.call_args.args[0] == "https://api.acedata.cloud" + contract["request_path"]
    )
