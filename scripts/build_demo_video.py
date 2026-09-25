"""Encode a silent annotated walkthrough from actual local browser screenshots.
This is a screen-based replay, not a continuous live interaction recording.
"""

from pathlib import Path
import subprocess, json, textwrap
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/submission"
TMP = ROOT / "tmp/video"
TMP.mkdir(parents=True, exist_ok=True)
scenes = [
    (
        "01-login",
        "Secure local access",
        "Sign in with an existing account. Each application role has its own permissions.",
    ),
    (
        "02-overview",
        "Evidence before confidence",
        "A fictional workspace. Screens replay saved real API output; review state is synthetic.",
    ),
    (
        "03-upload",
        "Upload PDF or DOCX",
        "Metadata, effective date and role scope travel with each immutable document version.",
    ),
    (
        "04-source",
        "Inspect extraction",
        "Source sections and requirement candidates remain separate and reviewable.",
    ),
    (
        "05-rule",
        "Review the requirement",
        "An exact source passage supports the approved rule; conditions and exceptions need review.",
    ),
    (
        "06-roles",
        "Configure job roles",
        "Business roles are distinct from administrator, reviewer and employee permissions.",
    ),
    (
        "07-matrix",
        "Build the approved matrix",
        "Only approved requirements from active applicable documents enter generation.",
    ),
    (
        "08-verification",
        "Verify structured facts",
        "Reviewed annotations support independent checks; free-form meaning still needs review.",
    ),
    (
        "09-plan",
        "Inspect real generated output",
        "The stored two-module API result shows coverage and traceability; it is not a fresh request.",
    ),
    (
        "14-assessment",
        "Learn, practice and assess",
        "Generated learning includes checklists, scenarios, practical tasks, quizzes and scoring rubrics.",
    ),
    (
        "15-citation-failure",
        "Make the validator disagree",
        "A deliberately corrupted source ID is a synthetic negative test. Python blocks the result.",
    ),
    (
        "16-conflict",
        "Resolve policy precedence",
        "Two reviewed values conflict. A documented reviewer decision is required.",
    ),
    (
        "17-quarantine",
        "Treat documents as untrusted data",
        "This actual adversarial PDF is quarantined. Its instructions cannot approve training.",
    ),
    (
        "10-compare",
        "Compare policy versions",
        "The deadline changed from two hours to one. Changed inputs do not get a consistency score.",
    ),
    (
        "11-selective",
        "Regenerate only affected learning",
        "One module is retained and one needs regeneration. Unchanged progress is eligible at publication.",
    ),
    (
        "12-learning",
        "Keep completion distinct",
        "Reading, checklist, quiz and human practical assessment determine employee completion.",
    ),
    (
        "13-reports",
        "Export reviewable evidence",
        "Filter progress and validation reports, then export CSV. Deployment is excluded from Phase 4.",
    ),
]
font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 22)
bold = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 26)
files = []
for i, (name, title, caption) in enumerate(scenes):
    screenshot = Image.open(OUT / "screenshots" / (name + ".png")).convert("RGB")
    screenshot = screenshot.resize((1280, 720))
    frame = Image.new("RGB", (1280, 840), "#153a2d")
    frame.paste(screenshot, (0, 0))
    draw = ImageDraw.Draw(frame)
    draw.text((26, 730), f"{i+1:02d} / {len(scenes):02d}   {title}", font=bold, fill="#d6eeaf")
    for line_no, line in enumerate(textwrap.wrap(caption, width=104)):
        draw.text((26, 767 + line_no * 28), line, font=font, fill="white")
    path = TMP / f"{i:02d}.png"
    frame.save(path)
    files.append(path)
concat = TMP / "scenes.txt"
concat.write_text(
    "".join("file '" + p.as_posix() + "'\nduration 10\n" for p in files)
    + "file '"
    + files[-1].as_posix()
    + "'\n",
    encoding="utf-8",
)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run(
    [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat),
        "-r",
        "24",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(OUT / "SkillSprint_local_walkthrough.mp4"),
    ],
    check=True,
    capture_output=True,
)
verify = subprocess.run(
    [
        ffmpeg,
        "-v",
        "error",
        "-i",
        str(OUT / "SkillSprint_local_walkthrough.mp4"),
        "-f",
        "null",
        "-",
    ],
    capture_output=True,
    text=True,
)
assert verify.returncode == 0, verify.stderr
(OUT / "VIDEO_NOTES.md").write_text(
    "# Local walkthrough video\n\n170-second silent annotated walkthrough built from actual browser screenshots. Saved real Phase 3 API output is replayed in an isolated demonstration database; decisions, negative cases and learner state are explicitly synthetic. This is not a continuous fresh-generation recording. No deployment is shown. For a live competition recording, follow DEMO_SCRIPT.md and demonstrate actual upload, generation and publication actions.\n\nEncoding: H.264, 1280x840, 24 fps. Full decode verified with FFmpeg.\n",
    encoding="utf-8",
)
print(
    json.dumps(
        {
            "video": str(OUT / "SkillSprint_local_walkthrough.mp4"),
            "scenes": len(scenes),
            "decode_verified": True,
        }
    )
)
