import subprocess
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Winnow Video Controller")

player_process = None
current_video = None

class PlayRequest(BaseModel):
    video_name: str

@app.post("/play")
def play_video(request: PlayRequest):
    global player_process, current_video
    
    video_path = os.path.join("videos", request.video_name)
    
    if player_process is not None and player_process.poll() is None:
        raise HTTPException(status_code=409, detail= "Video is already playing.")
        
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail=f"The file {request.video_name} was not found.")

    try:
        player_process = subprocess.Popen([r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe", "--play-and-exit", video_path])
        current_video = request.video_name
        return {"status": "success", "message": f"Playback started: {request.video_name}"}
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Error: VLC Player was not found on the system.")

@app.post("/stop")
def stop_video():
    global player_process, current_video
    if player_process is not None and player_process.poll() is None:
        player_process.terminate()
        player_process = None
        current_video = None
        return {"status": "success", "message": "Video playback stopped."}
    
    return {"status": "success", "message": "System is already idle."}

@app.get("/status")
def get_status():
    global player_process, current_video
    if player_process is not None and player_process.poll() is None:
        return {"state": "playing", "current_video": current_video}
    
    return {"state": "idle", "current_video": None}