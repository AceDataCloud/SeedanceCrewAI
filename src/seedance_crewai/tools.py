"""Service-specific schemas, request fields and media shape; shared safety semantics."""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal

from crewai.tools.tool_failure import ToolFailure
from pydantic import BaseModel, ConfigDict, Field

from seedance_crewai._base import RetrieveTaskInput, ServiceTool, https_urls


class TextContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["text"] = "text"
    text: str = Field(min_length=1, max_length=1000)


class MediaURL(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(min_length=1)


class ImageContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["image_url"] = "image_url"
    image_url: MediaURL
    role: Literal["first_frame", "last_frame", "reference_image"] | None = None


class AudioContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["audio_url"] = "audio_url"
    audio_url: MediaURL
    role: Literal["reference_audio"]


class VideoContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["video_url"] = "video_url"
    video_url: MediaURL
    role: Literal["reference_video"]


class GenerateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = Field(
        min_length=1, description="Current public Seedance model ID; passed unchanged"
    )
    content: list[
        Annotated[
            TextContent | ImageContent | AudioContent | VideoContent,
            Field(discriminator="type"),
        ]
    ] = Field(
        min_length=1,
        description="Structured text/image/audio/video content supported by the chosen model",
    )
    resolution: Literal["480p", "720p", "1080p", "4k"] | None = None
    ratio: Literal["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"] | None = (
        None
    )
    duration: int | None = Field(default=None, ge=-1, le=30)
    frames: int | None = Field(default=None, ge=29, le=289)
    seed: int | None = Field(default=None, ge=-1, le=4294967295)
    camerafixed: bool | None = None
    watermark: bool | None = None
    generate_audio: bool | None = None
    return_last_frame: bool | None = None


class _Tool(ServiceTool):
    service = "Seedance"
    task_path = "/seedance/tasks"

    def _media_urls(self, result: dict[str, Any]) -> list[str]:
        data = result.get("data") or {}
        content = data.get("content") or {} if isinstance(data, dict) else {}
        return https_urls(
            [data.get("video_url"), content.get("video_url")]
            if isinstance(data, dict)
            else []
        )


class SeedanceGenerateVideoTool(_Tool):
    name: str = "Seedance by Ace Data Cloud - Generate Video"
    description: str = "Submit one billable Seedance job. Save task_id, then use Retrieve Task on that same ID. Never repeat generation to poll; unknown timeouts require request-history inspection."
    args_schema: type[BaseModel] = GenerateInput
    max_usage_count: int | None = 1

    def _run(self, **parameters: Any) -> str | ToolFailure:
        payload = GenerateInput.model_validate(parameters).model_dump(exclude_none=True)
        payload["async"] = True
        body = self._request("/seedance/videos", payload)
        result = self._normalize(body, "", retrieved=False)
        return result if isinstance(result, ToolFailure) else json.dumps(result)


class SeedanceRetrieveTaskTool(_Tool):
    name: str = "Seedance by Ace Data Cloud - Retrieve Task"
    description: str = "Read an existing Seedance task_id, optionally wait up to 240 seconds. pending is not success. This never creates new media."
    args_schema: type[BaseModel] = RetrieveTaskInput

    def _run(self, task_id: str, wait_seconds: int = 0) -> str | ToolFailure:
        return self._retrieve(task_id, wait_seconds)
