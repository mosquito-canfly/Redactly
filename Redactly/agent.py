"""Agent: tool declarations, a single round-trip, and the full execution loop."""

import mimetypes

from google import genai
from google.genai import types
from PIL import Image

from redactly.config import require_gemini_key
from redactly.llm import MODEL, detect_sensitive_regions  # reuse the model that's already confirmed working
from redactly.ocr import extract_text_boxes
from redactly.classify import is_sensitive_regex
from redactly.redact import redact_boxes

_SYSTEM_INSTRUCTION = (
    "You are a screenshot redaction agent. Your job is to find and blur all "
    "sensitive information — emails, IC numbers, faces, names, addresses, "
    "keys, phone numbers. You have tools. Decide the FIRST action to take."
)

_BOX_SCHEMA = types.Schema(
    type="OBJECT",
    properties={
        "left": types.Schema(type="INTEGER"),
        "top": types.Schema(type="INTEGER"),
        "width": types.Schema(type="INTEGER"),
        "height": types.Schema(type="INTEGER"),
        "label": types.Schema(type="STRING"),
    },
    required=["left", "top", "width", "height"],
)

TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="ocr_image",
            description="Run OCR on the current image and return detected text with bounding boxes.",
        ),
        types.FunctionDeclaration(
            name="check_regex",
            description="Check whether a piece of text matches a high-confidence sensitive pattern (email, credit card, phone, API key, etc).",
            parameters=types.Schema(
                type="OBJECT",
                properties={"text": types.Schema(type="STRING", description="The text to check.")},
                required=["text"],
            ),
        ),
        types.FunctionDeclaration(
            name="detect_vision",
            description="Use vision to find sensitive regions (faces, IDs, etc) directly on the current image.",
        ),
        types.FunctionDeclaration(
            name="blur_regions",
            description="Blur the given list of boxes on the current image.",
            parameters=types.Schema(
                type="OBJECT",
                properties={"boxes": types.Schema(type="ARRAY", items=_BOX_SCHEMA)},
                required=["boxes"],
            ),
        ),
        types.FunctionDeclaration(
            name="finish",
            description="Signal that redaction is complete and no more actions are needed.",
        ),
    ])
]


def agent_single_step(image_path: str) -> None:
    """Send the image + tool set to Gemini and print the single action it picks."""
    try:
        width, height = Image.open(image_path).size
        mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        client = genai.Client(api_key=require_gemini_key())
        response = client.models.generate_content(
            model=MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                f"Image is {width}x{height} pixels.",
            ],
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_INSTRUCTION,
                tools=TOOLS,
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(mode="ANY"),
                ),
            ),
        )

        parts = response.candidates[0].content.parts
        for part in parts:
            if part.function_call:
                print(f"Tool call: {part.function_call.name}({dict(part.function_call.args or {})})")
            elif part.text:
                print(f"Text response: {part.text}")
    except Exception as e:
        print(f"ERROR: agent_single_step failed: {e}")


def _execute_tool(name: str, args: dict, image_path: str, output_path: str, accumulated_boxes: list[dict]):
    """Run one real tool call. Returns (result, is_finish). Never raises."""
    try:
        if name == "ocr_image":
            return extract_text_boxes(image_path), False
        if name == "check_regex":
            return {"is_sensitive": is_sensitive_regex(args.get("text", ""))}, False
        if name == "detect_vision":
            return detect_sensitive_regions(image_path), False
        if name == "blur_regions":
            accumulated_boxes.extend(args.get("boxes", []))
            redact_boxes(image_path, accumulated_boxes, output_path)
            return f"blurred {len(accumulated_boxes)} region(s) total, saved to {output_path}", False
        if name == "finish":
            return "acknowledged", True
        return f"unknown tool: {name}", False
    except Exception as e:
        return {"error": str(e)}, False


def run_agent(image_path: str, output_path: str, max_steps: int = 10) -> None:
    """Let Gemini drive redaction: it calls tools, we execute them and report back, until it calls finish."""
    width, height = Image.open(image_path).size
    mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    client = genai.Client(api_key=require_gemini_key())
    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_INSTRUCTION,
        tools=TOOLS,
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="ANY"),
        ),
    )

    contents = [
        types.Content(role="user", parts=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            types.Part.from_text(text=f"Image is {width}x{height} pixels."),
        ]),
    ]
    accumulated_boxes: list[dict] = []

    for step in range(1, max_steps + 1):
        try:
            response = client.models.generate_content(model=MODEL, contents=contents, config=config)
        except Exception as e:
            print(f"ERROR: Gemini call failed at step {step}: {e}")
            return

        model_content = response.candidates[0].content
        contents.append(model_content)
        calls = [part.function_call for part in model_content.parts if part.function_call]

        if not calls:
            text = "".join(part.text for part in model_content.parts if part.text)
            print(f"[step {step}] Gemini returned text instead of a tool call: {text!r}")
            break

        finished = False
        response_parts = []
        for call in calls:
            args = dict(call.args or {})
            print(f"[step {step}] Gemini called: {call.name}({args})")
            result, is_finish = _execute_tool(call.name, args, image_path, output_path, accumulated_boxes)
            print(f"[step {step}]   -> {result}")
            response_parts.append(types.Part.from_function_response(name=call.name, response={"result": result}))
            finished = finished or is_finish

        contents.append(types.Content(role="user", parts=response_parts))

        if finished:
            print(f"[step {step}] Agent signaled finish.")
            return
    else:
        print(f"WARNING: agent hit max_steps ({max_steps}) without calling finish. Output may be incomplete.")


if __name__ == "__main__":
    # ponytail: temporary manual hook for this step; real CLI wiring comes later
    import sys
    agent_single_step(sys.argv[1] if len(sys.argv) > 1 else "samples/images.jpeg")
