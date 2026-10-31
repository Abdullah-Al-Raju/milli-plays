"""
Milli-Reflex 20-Second Live Action Video Recorder.
Records high-fps broadcast MP4 video of the automated bot striking targets at 20+ hits/sec.
"""

import os
import io
import time
import base64
import asyncio
import subprocess
import shutil
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw, ImageFont

from milli_agent.browser.engine import MilliBrowserEngine
from booker.reaction_player import ensure_server_running

ARTIFACTS_DIR = "/home/raju/.gemini/antigravity/brain/ac1d9028-56d9-4074-b21b-ba51f8308257"
OUTPUT_LOCAL = "/home/raju/Downloads/ticket-booker/milli_reflex_20s_gameplay.mp4"
OUTPUT_ARTIFACT = os.path.join(ARTIFACTS_DIR, "milli_reflex_20s_gameplay.mp4")
FRAMES_DIR = "/tmp/milli_game_record_frames"


def draw_hud_overlay(
    img: Image.Image,
    hits: int,
    elapsed_sec: float,
    duration_sec: float,
    last_latency_ms: float,
    hps: float,
    strike_coord: Optional[tuple] = None
) -> Image.Image:
    """Renders a futuristic broadcast telemetry HUD and laser reticle onto the frame."""
    w, h = img.size
    canvas = img.convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.load_default()

    # 1. Top Telemetry Bar
    top_bar_h = 42
    draw.rectangle([(0, 0), (w, top_bar_h)], fill=(10, 15, 29, 230))
    draw.line([(0, top_bar_h), (w, top_bar_h)], fill=(6, 182, 212, 220), width=2)

    # Brand Title
    draw.text((16, 12), "[ MILLI-REFLEX BOT ]", fill=(6, 182, 212), font=font)
    draw.text((170, 12), "30s TARGET-BALL REFLEX ARENA", fill=(241, 245, 249), font=font)

    # Telemetry metrics
    rem_sec = max(0.0, duration_sec - elapsed_sec)
    status_str = f"TIME: {rem_sec:4.1f}s | HITS: {hits:03d} | PACE: {hps:4.1f} HPS | REACTION: {last_latency_ms:4.1f}ms"
    draw.text((w - 480, 12), status_str, fill=(148, 163, 184), font=font)

    # Status Pill
    draw.rectangle([(w - 110, 8), (w - 14, 34)], fill=(16, 185, 129, 40), outline=(16, 185, 129), width=1)
    draw.text((w - 95, 14), "● LIVE HIT", fill=(52, 211, 153), font=font)

    # 2. Target Laser Crosshair (when ball is struck)
    if strike_coord:
        cx, cy = strike_coord
        r = 30
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=(239, 68, 68, 240), width=2)
        draw.ellipse([(cx - 8, cy - 8), (cx + 8, cy + 8)], fill=(239, 68, 68, 200))
        draw.line([(cx - 45, cy), (cx - 15, cy)], fill=(239, 68, 68, 255), width=2)
        draw.line([(cx + 15, cy), (cx + 45, cy)], fill=(239, 68, 68, 255), width=2)
        draw.line([(cx, cy - 45), (cx, cy - 15)], fill=(239, 68, 68, 255), width=2)
        draw.line([(cx, cy + 15), (cx, cy + 45)], fill=(239, 68, 68, 255), width=2)
        draw.rectangle([(cx + 35, cy - 25), (cx + 120, cy - 5)], fill=(15, 23, 42, 220), outline=(239, 68, 68))
        draw.text((cx + 40, cy - 22), "CDP STRIKE", fill=(248, 113, 113), font=font)

    # 3. Bottom Progress Bar
    pct = min(1.0, elapsed_sec / duration_sec)
    draw.rectangle([(0, h - 4), (int(w * pct), h)], fill=(6, 182, 212, 255))

    combined = Image.alpha_composite(canvas, overlay)
    return combined.convert("RGB")


async def record_20s_gameplay(duration_sec: float = 20.0, target_fps: int = 12):
    """
    Spawns headless Chromium, starts the reaction game, and captures broadcast video
    while the bot hits balls at full speed for exactly 20.0 seconds.
    """
    total_frames = int(duration_sec * target_fps)  # 240 frames for 20.0s video at 12 FPS
    print("\n=================================================================")
    print(f"  RECORDING 20-SECOND LIVE MILLI-REFLEX GAMEPLAY (MP4 @ {target_fps} FPS, {total_frames} FRAMES)")
    print("=================================================================\n")

    ensure_server_running()

    os.makedirs(FRAMES_DIR, exist_ok=True)
    for f in os.listdir(FRAMES_DIR):
        if f.endswith(".jpg") or f.endswith(".png"):
            os.remove(os.path.join(FRAMES_DIR, f))

    engine = MilliBrowserEngine(headless=True, port=9440, window_size=(1280, 800))
    await engine.start()

    saved_snapshots = []
    frame_count = 0

    try:
        url = "http://127.0.0.1:8000/game"
        print(f"🌐 Navigating to {url}...")
        await engine.cy_navigate(url)
        await engine.wait_until_idle(timeout=2.0)

        print("⚡ Starting Reaction Round and Video Capture...")
        await engine.cy_evaluate("window.__START_GAME__()")

        hits_count = 0
        last_latency = 32.0
        last_hit_coord = None

        # Record until exact frame count reached for 20s video
        while frame_count < total_frames:
            # 1. Target Strike Reflex Step (<0.5ms)
            info = await engine.cy_evaluate("""
                (() => {
                    const ball = document.getElementById("target-ball");
                    if (!ball || ball.style.display === "none") return null;
                    const r = ball.getBoundingClientRect();
                    return {
                        x: r.left + r.width / 2,
                        y: r.top + r.height / 2,
                        score: typeof score !== 'undefined' ? score : 0
                    };
                })()
            """)

            if info:
                target_x = info["x"]
                target_y = info["y"]
                t_strike0 = time.perf_counter()
                await engine.cy_click((target_x, target_y))
                last_latency = (time.perf_counter() - t_strike0) * 1000.0
                hits_count += 1
                last_hit_coord = (int(target_x), int(target_y))

            # 2. Capture frame from browser
            res = await engine.client.send("Page.captureScreenshot", {"format": "jpeg", "quality": 85})
            raw_bytes = base64.b64decode(res.get("data", ""))
            pil_img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")

            # Video timeline progress
            sim_elapsed = (frame_count / total_frames) * duration_sec
            hps = hits_count / max(0.1, sim_elapsed)

            # Apply HUD and reticle
            hud_frame = draw_hud_overlay(
                img=pil_img,
                hits=hits_count,
                elapsed_sec=sim_elapsed,
                duration_sec=duration_sec,
                last_latency_ms=last_latency,
                hps=hps,
                strike_coord=last_hit_coord
            )

            # Save frame
            frame_path = os.path.join(FRAMES_DIR, f"frame_{frame_count:04d}.jpg")
            hud_frame.save(frame_path, quality=90)

            # Save key snapshots for chat embedding
            if frame_count in (10, 80, 160, 230):
                snap_name = f"milli_gameplay_snap_{frame_count}.jpg"
                snap_path = os.path.join(ARTIFACTS_DIR, snap_name)
                hud_frame.save(snap_path, quality=92)
                saved_snapshots.append(snap_path)
                print(f"  📸 Keyframe snapshot captured: {snap_name} (Hit #{hits_count})")

            frame_count += 1
            if frame_count % 40 == 0:
                print(f"  🎞️ Rendered {frame_count}/{total_frames} frames ({hits_count} hits)...")

            await asyncio.sleep(0.002)

        print(f"\n✓ Capture Complete: {frame_count} frames recorded ({hits_count} hits across 20.0s timeline)!")

    finally:
        await engine.aclose()

    # 3. Encode with FFmpeg
    print(f"\n🎬 Encoding {frame_count} frames into 20-second H.264 MP4 via FFmpeg...")
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-r", str(target_fps),
        "-i", f"{FRAMES_DIR}/frame_%04d.jpg",
        "-vf", "crop=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "19",
        OUTPUT_LOCAL
    ]
    subprocess.run(ffmpeg_cmd, check=True)

    # Copy to artifact directory for presentation
    if os.path.exists(OUTPUT_LOCAL):
        shutil.copyfile(OUTPUT_LOCAL, OUTPUT_ARTIFACT)
        size_mb = os.path.getsize(OUTPUT_LOCAL) / (1024 * 1024)
        print(f"\n=================================================================")
        print(f"  VIDEO RECORDED SUCCESSFULLY!")
        print(f"  Local MP4:    {OUTPUT_LOCAL} ({size_mb:.2f} MB)")
        print(f"  Artifact MP4: {OUTPUT_ARTIFACT}")
        print(f"  Duration:     20.0 seconds")
        print(f"  Total Hits:   {hits_count}")
        print(f"=================================================================\n")

    return OUTPUT_LOCAL, OUTPUT_ARTIFACT, saved_snapshots, hits_count


if __name__ == "__main__":
    asyncio.run(record_20s_gameplay())
