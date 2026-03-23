import subprocess
import os
import socket
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Winnow Video Controller")

player_process = None
current_video = None
is_paused = False

VIDEOS_DIR = Path("videos").resolve()
VLC_PATH = r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
VLC_RC_HOST = "127.0.0.1"
VLC_RC_PORT = 4212

class PlayRequest(BaseModel):
    video_name: str


def resolve_video_path(video_name: str) -> Path:
    candidate = (VIDEOS_DIR / video_name).resolve()

    if VIDEOS_DIR != candidate and VIDEOS_DIR not in candidate.parents:
        raise HTTPException(status_code=400, detail="Invalid video path.")

    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail=f"The file {video_name} was not found.")

    return candidate


def send_vlc_command(command: str) -> None:
    try:
        with socket.create_connection((VLC_RC_HOST, VLC_RC_PORT), timeout=1.5) as sock:
            sock.sendall(f"{command}\n".encode("utf-8"))
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Failed to control VLC player.") from exc

@app.post("/play")
def play_video(request: PlayRequest):
    global player_process, current_video, is_paused

    video_path = resolve_video_path(request.video_name)

    if player_process is not None and player_process.poll() is None:
        raise HTTPException(status_code=409, detail="Video is already playing.")

    try:
        player_process = subprocess.Popen(
            [
                VLC_PATH,
                "--play-and-exit",
                "--extraintf",
                "rc",
                "--rc-host",
                f"{VLC_RC_HOST}:{VLC_RC_PORT}",
                str(video_path),
            ]
        )
        current_video = request.video_name
        is_paused = False
        return {"status": "success", "message": f"Playback started: {request.video_name}"}
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Error: VLC Player was not found on the system.")

@app.post("/stop")
def stop_video():
    global player_process, current_video, is_paused
    if player_process is not None and player_process.poll() is None:
        player_process.terminate()
        player_process = None
        current_video = None
        is_paused = False
        return {"status": "success", "message": "Video playback stopped."}
    
    return {"status": "success", "message": "System is already idle."}


@app.post("/pause")
def pause_video():
    global is_paused

    if player_process is None or player_process.poll() is not None:
        raise HTTPException(status_code=409, detail="No video is currently playing.")
    if is_paused:
        return {"status": "success", "message": "Video is already paused."}

    send_vlc_command("pause")
    is_paused = True
    return {"status": "success", "message": "Video playback paused."}


@app.post("/resume")
def resume_video():
    global is_paused

    if player_process is None or player_process.poll() is not None:
        raise HTTPException(status_code=409, detail="No video is currently playing.")
    if not is_paused:
        return {"status": "success", "message": "Video is already playing."}

    send_vlc_command("pause")
    is_paused = False
    return {"status": "success", "message": "Video playback resumed."}

@app.get("/status")
def get_status():
    if player_process is not None and player_process.poll() is None:
        state = "paused" if is_paused else "playing"
        return {"state": state, "current_video": current_video}

    return {"state": "idle", "current_video": None}