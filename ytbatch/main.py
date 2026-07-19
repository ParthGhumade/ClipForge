import os
import sys
import multiprocessing
import concurrent.futures
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.console import Console
from rich.panel import Panel

from encoder import get_best_encoder
from processor import process_video

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, 'assets')
    input_dir = os.path.join(base_dir, 'input')
    output_dir = os.path.join(base_dir, 'output')

    intro_path = os.path.join(assets_dir, 'intro.mp4')
    outro_path = os.path.join(assets_dir, 'outro.mp4')

    console = Console()

    # 1. Verify assets
    if not os.path.exists(intro_path) or not os.path.exists(outro_path):
        console.print("[red]Error: Assets missing.[/red]")
        console.print(f"Ensure both exist:\n- {intro_path}\n- {outro_path}")
        sys.exit(1)

    # 2. Scan input directory
    supported_formats = ('.mp4', '.mkv', '.mov')
    try:
        files = os.listdir(input_dir)
    except FileNotFoundError:
        console.print(f"[red]Error: Input directory not found: {input_dir}[/red]")
        sys.exit(1)

    video_files = [f for f in files if f.lower().endswith(supported_formats)]
    
    if not video_files:
        console.print("[yellow]No supported videos found in input directory.[/yellow]")
        sys.exit(0)

    # 3. Determine encoder and workers
    encoder = get_best_encoder()
    # CPU Cores - 1, minimum 1
    worker_count = max(1, multiprocessing.cpu_count() - 1)
    
    # Pre-calculate encoder display name
    encoder_display = "Intel Quick Sync" if encoder == 'h264_qsv' else "libx264"

    # 4. Process videos with a progress bar
    total_videos = len(video_files)
    completed = 0
    current_file_display = ""

    # Set up Rich progress
    progress = Progress(
        TextColumn("[bold blue]Processing Videos"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        TimeRemainingColumn(),
        console=console
    )

    task_id = progress.add_task("process", total=total_videos)
    
    # We use a custom render loop to display the extra info panel below the progress bar
    # Alternatively, we can just use progress.console.print inside the with block, 
    # but Rich's Progress allows grouping with a Panel or Group. Let's just update the description.
    # To match the PRD exactly:
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Processing Videos
    # ███████████████░░░░░░░░
    # 18 / 50 Completed
    # Current:
    # lecture18.mp4
    # Workers:
    # 15
    # Encoder:
    # Intel Quick Sync
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # A simple way to approximate this in Rich without building a complex layout is to use custom columns.
    # Or we can just use the standard progress and print the static info before it.
    
    console.print(Panel.fit(
        f"Workers: {worker_count}\nEncoder: {encoder_display}",
        title="YTBatch Info"
    ))

    with progress:
        with concurrent.futures.ProcessPoolExecutor(max_workers=worker_count) as executor:
            # Submit all tasks
            futures = {}
            for video_file in video_files:
                input_path = os.path.join(input_dir, video_file)
                output_path = os.path.join(output_dir, video_file)
                
                future = executor.submit(
                    process_video, 
                    input_path, 
                    intro_path, 
                    outro_path, 
                    output_path, 
                    encoder
                )
                futures[future] = video_file

            for future in concurrent.futures.as_completed(futures):
                video_file = futures[future]
                completed += 1
                progress.update(task_id, advance=1, description=f"[bold blue]Current: {video_file}")
                
                # Retrieve result to catch any exceptions
                try:
                    success = future.result()
                    if not success:
                        progress.console.print(f"[red]Failed to process {video_file}[/red]")
                except Exception as exc:
                    progress.console.print(f"[red]Exception processing {video_file}: {exc}[/red]")

    console.print("[green]Processing complete![/green]")

if __name__ == '__main__':
    # Add support for freezing (e.g., PyInstaller) if needed later
    multiprocessing.freeze_support()
    main()
