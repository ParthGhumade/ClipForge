import subprocess
import os

def get_framerate(filepath: str) -> float:
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=r_frame_rate',
            '-of', 'default=noprint_wrappers=1:nokey=1', filepath
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        rate_str = result.stdout.strip()
        if '/' in rate_str:
            num, den = rate_str.split('/')
            return float(num) / float(den)
        else:
            return float(rate_str)
    except Exception:
        return 30.0

def get_standard_fps(raw_fps: float) -> int:
    standard_rates = [24, 25, 30, 50, 60, 120, 144, 240]
    for rate in standard_rates:
        # Give a 1.0 margin for fractional framerates like 29.97 or 59.94
        if rate >= raw_fps - 1.0:
            return rate
    return 60

def process_video(input_path: str, intro_path: str, outro_path: str, output_path: str, encoder: str) -> bool:
    """
    Processes a single video by prepending an intro and appending an outro.
    Returns True if successful, False otherwise.
    """
    if os.path.exists(output_path):
        return True

    # Determine highest framerate to always prefer upscaling
    fps_intro = get_framerate(intro_path)
    fps_input = get_framerate(input_path)
    fps_outro = get_framerate(outro_path)
    
    max_raw_fps = max(fps_intro, fps_input, fps_outro)
    target_fps = get_standard_fps(max_raw_fps)

    # We use a robust filter_complex to scale all videos to 1920x1080,
    # normalize framerate to the max standard fps,
    # and normalize audio to 48000Hz stereo to prevent concat errors.
    filter_complex = (
        f"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={target_fps}[v0];"
        f"[1:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={target_fps}[v1];"
        f"[2:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={target_fps}[v2];"
        "[0:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a0];"
        "[1:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a1];"
        "[2:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a2];"
        "[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[v][a]"
    )

    cmd = [
        'ffmpeg',
        '-y', # Overwrite output if somehow it exists and wasn't caught by os.path.exists
        '-i', intro_path,
        '-i', input_path,
        '-i', outro_path,
        '-filter_complex', filter_complex,
        '-map', '[v]',
        '-map', '[a]',
        '-c:v', encoder,
        output_path
    ]

    try:
        # Run FFmpeg, suppressing output unless there is an error
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        # If it fails, print the stderr for debugging, but in MVP we mostly just fail silently or log it if needed
        # We'll print it so the user can see if something goes wrong
        print(f"Error processing {input_path}:\n{e.stderr}")
        return False
