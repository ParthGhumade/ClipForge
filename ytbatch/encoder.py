import subprocess

def get_best_encoder() -> str:
    """
    Checks if Intel Quick Sync Video (h264_qsv) is available in FFmpeg.
    Falls back to libx264 if not available.
    """
    try:
        # Run ffmpeg -encoders and search for h264_qsv
        result = subprocess.run(
            ['ffmpeg', '-encoders'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        if 'h264_qsv' in result.stdout:
            return 'h264_qsv'
    except FileNotFoundError:
        # FFmpeg not found, but we will handle this in main.py
        pass

    return 'libx264'
