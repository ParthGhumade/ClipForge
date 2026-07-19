import subprocess
import os

def process_video(input_path: str, intro_path: str, outro_path: str, output_path: str, encoder: str) -> bool:
    """
    Processes a single video by prepending an intro and appending an outro.
    Returns True if successful, False otherwise.
    """
    if os.path.exists(output_path):
        return True

    # We use a robust filter_complex to scale all videos to 1920x1080 
    # and normalize audio to 48000Hz stereo to prevent concat errors.
    filter_complex = (
        "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[v0];"
        "[1:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[v1];"
        "[2:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[v2];"
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
