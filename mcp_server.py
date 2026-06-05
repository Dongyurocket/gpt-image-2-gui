"""image2 MCP server.

Exposes image2's text-to-image and image-edit capabilities over the MCP
stdio protocol. Reuses the request/response helpers in image2_gui.py so
behaviour stays consistent with the GUI tool. Configuration (base_url,
api_key, model, output_dir, proxy, etc.) is read from image2/config.json
at every tool invocation, so the GUI is still the single source of truth
for credentials.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# image2_gui is a tkinter-based GUI module; importing it is fine because the
# class is only defined, not instantiated, at import time.
from image2_gui import (  # type: ignore[import-not-found]
    DEFAULT_CONFIG,
    add_common_optional_fields,
    auth_headers,
    build_endpoint,
    build_session,
    download_image,
    guess_mime,
    load_config,
    prepare_edit_uploads,
    resolve_output_dir,
    save_b64_image,
)

from mcp.server.fastmcp import FastMCP  # type: ignore[import-not-found]

mcp = FastMCP("image2")

API_TIMEOUT_SEC = 600


def _require_config() -> dict[str, str]:
    """Load image2/config.json and validate base_url + api_key.

    Returns a fully-populated config dict. Raises a clear RuntimeError on
    misconfiguration so the MCP client gets a human-readable message
    instead of a stack trace.
    """
    config = load_config()
    base_url = (config.get("base_url") or "").strip()
    api_key = (config.get("api_key") or "").strip()
    if not base_url or base_url == DEFAULT_CONFIG["base_url"]:
        raise RuntimeError(
            "image2 配置未完成：缺少 base_url。\n"
            "请先在 image2 GUI 中填写 Base URL 并点击「保存配置」，"
            f"或直接编辑 {Path(__file__).parent / 'config.json'}。"
        )
    if not api_key:
        raise RuntimeError(
            "image2 配置未完成：api_key 为空。\n"
            "请先在 image2 GUI 中填写 API Key 并点击「保存配置」，"
            f"或直接编辑 {Path(__file__).parent / 'config.json'}。"
        )
    return config


def _do_generation(config: dict[str, str], prompt: str) -> Path:
    url = build_endpoint(config["base_url"], "generations")
    payload: dict[str, Any] = {
        "model": config.get("model") or "gpt-image-2",
        "prompt": prompt,
        "n": 1,
        "size": config.get("size") or "auto",
        "quality": config.get("quality") or "auto",
        "output_format": config.get("output_format") or "png",
        "response_format": config.get("response_format") or "url",
    }
    add_common_optional_fields(payload, config)

    session = build_session(config)
    response = session.post(
        url,
        headers=auth_headers(config["api_key"]),
        json=payload,
        timeout=API_TIMEOUT_SEC,
    )
    return _handle_api_response(response, config)


def _do_edit(
    config: dict[str, str],
    prompt: str,
    image_paths: list[str],
    mask_path: str,
) -> Path:
    url = build_endpoint(config["base_url"], "edits")
    data: dict[str, str] = {
        "model": config.get("model") or "gpt-image-2",
        "prompt": prompt,
        "n": "1",
        "size": config.get("size") or "auto",
        "quality": config.get("quality") or "auto",
        "output_format": config.get("output_format") or "png",
        "response_format": config.get("response_format") or "url",
    }
    add_common_optional_fields(data, config)
    if config.get("input_fidelity"):
        data["input_fidelity"] = config["input_fidelity"]

    opened_files: list[Any] = []
    temp_files: list[Path] = []
    try:
        upload_image_paths, upload_mask_path, temp_files = prepare_edit_uploads(
            image_paths, mask_path, config
        )
        files: list[tuple[str, tuple[str, Any, str]]] = []
        image_field = "image" if len(upload_image_paths) == 1 else "image[]"
        for upload_image_path in upload_image_paths:
            image = open(upload_image_path, "rb")
            opened_files.append(image)
            files.append(
                (
                    image_field,
                    (Path(upload_image_path).name, image, guess_mime(str(upload_image_path))),
                )
            )
        if upload_mask_path:
            mask = open(upload_mask_path, "rb")
            opened_files.append(mask)
            files.append(("mask", (Path(upload_mask_path).name, mask, "image/png")))

        session = build_session(config)
        response = session.post(
            url,
            headers=auth_headers(config["api_key"]),
            data=data,
            files=files,
            timeout=API_TIMEOUT_SEC,
        )
        return _handle_api_response(response, config)
    finally:
        for file_obj in opened_files:
            try:
                file_obj.close()
            except OSError:
                pass
        for temp_file in temp_files:
            try:
                temp_file.unlink(missing_ok=True)
            except OSError:
                pass


def _handle_api_response(response: Any, config: dict[str, str]) -> Path:
    text_preview = response.text[:800] if getattr(response, "text", None) else ""
    if response.status_code >= 400:
        raise RuntimeError(f"API 请求失败: HTTP {response.status_code}\n{text_preview}")

    try:
        body = response.json()
    except ValueError as exc:
        raise RuntimeError(f"响应不是 JSON:\n{text_preview}") from exc

    data = body.get("data")
    if not isinstance(data, list) or not data:
        raise RuntimeError(
            f"响应中没有 data[0]:\n{json.dumps(body, ensure_ascii=False, indent=2)[:1200]}"
        )

    item = data[0]
    output_dir = resolve_output_dir(config.get("output_dir", DEFAULT_CONFIG["output_dir"]))
    output_dir.mkdir(parents=True, exist_ok=True)

    if item.get("url"):
        return download_image(item["url"], output_dir, config.get("output_format", "png"), config)
    if item.get("b64_json"):
        return save_b64_image(item["b64_json"], output_dir, config.get("output_format", "png"))

    raise RuntimeError(
        f"data[0] 中既没有 url 也没有 b64_json:\n"
        f"{json.dumps(item, ensure_ascii=False, indent=2)[:1200]}"
    )


@mcp.tool()
def generate_image(prompt: str) -> str:
    """Generate an image from a text prompt via the image2 backend.

    Reads base_url, api_key, model, size, quality, output_format and
    response_format from image2/config.json. Returns the absolute path of
    the saved image on success. Prompt is sent verbatim to the upstream
    API; the API may rewrite it and the result is reflected in the
    returned file.
    """
    config = _require_config()
    saved = _do_generation(config, prompt)
    return f"图片已保存: {saved}"


@mcp.tool()
def edit_image(prompt: str, image_paths: list[str], mask_path: str = "") -> str:
    """Edit or remix an image via the image2 backend.

    image_paths is the list of absolute paths to local reference images
    (PNG / JPG / JPEG / WebP). mask_path is an optional absolute path to
    a PNG mask; leave it empty when no mask is required. Returns the
    absolute path of the saved image on success.
    """
    if not image_paths:
        raise RuntimeError("image_paths 不能为空，至少需要一张参考图。")
    config = _require_config()
    saved = _do_edit(config, prompt, image_paths, mask_path)
    return f"图片已保存: {saved}"


if __name__ == "__main__":
    try:
        mcp.run(transport="stdio")
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"image2 MCP server 启动失败: {exc}\n")
        sys.exit(1)
