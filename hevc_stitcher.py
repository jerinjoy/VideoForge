#!/usr/bin/env python3

# Stitches together multiple video files (MOV/MP4) and encodes them
# to HEVC format.

# Created with Claude and ChatGPT.

import argparse
import os
import subprocess
import tempfile
import shutil
import json
from datetime import timedelta, datetime


class Colors:
    """ANSI color codes for terminal output"""

    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def get_resolution_and_fps(resolution, fps):
    """
    Determines the resolution and frame rate based on user input.

    Args:
      resolution: String representing the desired resolution (480p, 720p, 1080p, 4K).
      fps: Integer representing the desired frame rate.

    Returns:
      A tuple containing the width, height, and frame rate.
    """
    if resolution == "480p":
        width, height = 640, 360
    elif resolution == "720p":
        width, height = 1280, 720
    elif resolution == "1080p":
        width, height = 1920, 1080
    elif resolution == "4K":
        width, height = 3840, 2160
    else:
        raise ValueError(f"Invalid resolution: {resolution}")

    return width, height, fps


def get_video_details(file_path):
    """
    Gets comprehensive details about a video file using ffprobe.

    Args:
      file_path: Path to the video file.

    Returns:
      A dictionary containing video details.

    Raises:
      VideoProcessingError: If file analysis fails
    """
    if not os.path.exists(file_path):
        raise VideoProcessingError(f"File does not exist: {file_path}")

    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,pix_fmt,color_space,color_transfer,color_primaries,duration",
            "-of",
            "json",
            file_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        if not data.get("streams"):
            raise VideoProcessingError(f"No video stream found in {file_path}")

        stream = data["streams"][0]
        fps_ratio = stream.get("r_frame_rate", "0/1").split("/")

        try:
            fps = (
                round(float(fps_ratio[0]) / float(fps_ratio[1]), 3)
                if len(fps_ratio) == 2
                else 0
            )
        except (ValueError, ZeroDivisionError):
            raise VideoProcessingError(f"Invalid frame rate data in {file_path}")

        if not stream.get("width") or not stream.get("height"):
            raise VideoProcessingError(f"Invalid resolution data in {file_path}")

        # Get modification time (matches ls on Linux)
        mod_time = os.path.getmtime(file_path)
        creation_date = datetime.fromtimestamp(mod_time)

        return {
            "width": stream["width"],
            "height": stream["height"],
            "fps": fps,
            "pixel_format": stream.get("pix_fmt", "unknown"),
            "color_space": stream.get("color_space", "unknown"),
            "color_transfer": stream.get("color_transfer", "unknown"),
            "color_primaries": stream.get("color_primaries", "unknown"),
            "duration": float(stream.get("duration", 0)),
            "creation_date": creation_date,
        }

    except subprocess.CalledProcessError as e:
        raise VideoProcessingError(
            f"Failed to analyze {file_path}: {e.stderr if e.stderr else str(e)}"
        )
    except json.JSONDecodeError as e:
        raise VideoProcessingError(f"Invalid ffprobe output for {file_path}: {e}")


def format_duration(seconds):
    """Convert duration in seconds to HH:MM:SS format"""
    return str(timedelta(seconds=int(float(seconds))))


def print_command(cmd):
    """Print a command in blue color with proper formatting"""
    formatted_cmd = []
    for item in cmd:
        if item.startswith("-"):
            formatted_cmd.extend(["\n    ", item])
        else:
            formatted_cmd.append(" " + item)

    print(f"\n{Colors.BLUE}Running ffmpeg command:{Colors.END}")
    print(f"{Colors.BLUE}{''.join(formatted_cmd)}{Colors.END}\n")


def print_file_details(filename, details):
    """Print formatted file details"""
    is_hdr = (
        details["color_transfer"] in ["smpte2084", "arib-std-b67"]
        or details["color_primaries"] == "bt2020"
    )

    print(f"\n{Colors.BOLD}{filename}{Colors.END}")
    print(
        f"├─ {Colors.GREEN}Resolution:{Colors.END} {details['width']}x{details['height']}"
    )
    print(f"├─ {Colors.GREEN}FPS:{Colors.END} {details['fps']}")
    print(
        f"├─ {Colors.GREEN}Duration:{Colors.END} {format_duration(details['duration'])}"
    )
    print(
        f"├─ {Colors.GREEN}Creation Date:{Colors.END} {details['creation_date'].strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print(f"├─ {Colors.GREEN}Pixel Format:{Colors.END} {details['pixel_format']}")
    print(f"├─ {Colors.GREEN}Color Space:{Colors.END} {details['color_space']}")
    print(f"├─ {Colors.GREEN}Color Transfer:{Colors.END} {details['color_transfer']}")
    print(f"├─ {Colors.GREEN}Color Primaries:{Colors.END} {details['color_primaries']}")
    print(f"└─ {Colors.GREEN}HDR:{Colors.END} {'Yes' if is_hdr else 'No'}")


def is_video_file(filename):
    """
    Checks if a file is a video file (mov or mp4) using case-insensitive comparison.

    Args:
      filename: Name of the file to check.

    Returns:
      Boolean indicating if the file is a video file.
    """
    return filename.lower().endswith((".mov", ".mp4"))


def get_sorted_video_files(input_dir, sort_by="filename"):
    """
    Gets a sorted list of video files based on the specified sorting method.

    Args:
      input_dir: Path to the directory containing the video files.
      sort_by: String indicating the sorting method ('filename' or 'creation_date').

    Returns:
      A list of tuples containing (filename, creation_date) sorted according to sort_by.

    Raises:
        VideoProcessingError: If directory access fails or sort_by is invalid
    """
    if sort_by not in ["filename", "creation_date"]:
        raise VideoProcessingError(f"Invalid sort_by value: {sort_by}")

    try:
        video_files = []
        for filename in os.listdir(input_dir):
            if is_video_file(filename):
                file_path = os.path.join(input_dir, filename)
                try:
                    mod_time = os.path.getmtime(file_path)
                    video_files.append((filename, datetime.fromtimestamp(mod_time)))
                except OSError as e:
                    raise VideoProcessingError(
                        f"Failed to get modification time for {filename}: {e}"
                    )

        if sort_by == "creation_date":
            return sorted(video_files, key=lambda x: x[1])
        return sorted(video_files, key=lambda x: x[0])

    except OSError as e:
        raise VideoProcessingError(f"Failed to access directory {input_dir}: {e}")


def verify_resolutions(input_dir, target_width, target_height):
    """
    Verifies that all video files in the input directory match the target resolution.

    Args:
      input_dir: Path to the directory containing the video files.
      target_width: Target width for the videos.
      target_height: Target height for the videos.

    Returns:
      A list of files with mismatched resolutions.
    """
    mismatched_files = []
    print(f"\n{Colors.BOLD}Analyzing input files:{Colors.END}")

    for filename in sorted(os.listdir(input_dir)):
        if is_video_file(filename):
            file_path = os.path.join(input_dir, filename)
            try:
                details = get_video_details(file_path)
                print_file_details(filename, details)

                if (
                    details["width"] != target_width
                    or details["height"] != target_height
                ):
                    mismatched_files.append(
                        (filename, (details["width"], details["height"]))
                    )
            except Exception as e:
                print(
                    f"{Colors.RED}Warning: Could not check details of {filename}: {e}{Colors.END}"
                )

    return mismatched_files


def concatenate_and_encode(
    input_dir, output_file, enable_hdr, resolution, fps, sort_by, dry_run=False
):
    """
    Concatenates video files in the input directory and encodes them to HEVC.

    Args:
      input_dir: Path to the directory containing the video files.
      output_file: Path to the desired output HEVC file.
      enable_hdr: Boolean flag to enable or disable HDR encoding.
      resolution: String representing the desired resolution (480p, 720p, 1080p, 4K).
      fps: Integer representing the desired frame rate.
      sort_by: String indicating the sorting method ('filename' or 'creation_date').
      dry_run: If True, only preview the operations without executing the ffmpeg command.
    """
    try:
        # Check if ffmpeg and ffprobe are executable
        for tool in ["ffmpeg", "ffprobe"]:
            if not shutil.which(tool):
                raise FileNotFoundError(f"{tool} is not found")
    except FileNotFoundError as e:
        print(
            f"{Colors.RED}Error: {e}. Please install the required tools and ensure they're in your system's PATH.{Colors.END}"
        )
        exit(1)

    # Get target resolution
    target_width, target_height, fps = get_resolution_and_fps(resolution, fps)
    print(f"\n{Colors.BOLD}Target Settings:{Colors.END}")
    print(f"├─ Resolution: {target_width}x{target_height}")
    print(f"├─ FPS: {fps}")
    print(f"├─ HDR: {'Yes' if enable_hdr else 'No'}")
    print(f"└─ Sort by: {sort_by}")

    # Verify input file resolutions
    mismatched_files = verify_resolutions(input_dir, target_width, target_height)
    if mismatched_files:
        print(
            f"\n{Colors.RED}Error: The following files don't match the target resolution "
            + f"({target_width}x{target_height}):{Colors.END}"
        )
        for filename, (width, height) in mismatched_files:
            print(f"  - {filename}: {width}x{height}")
        exit(1)

    # Get sorted video files
    video_files = get_sorted_video_files(input_dir, sort_by)
    if not video_files:
        print(
            f"{Colors.RED}Error: No .mov or .mp4 files found in {input_dir}{Colors.END}"
        )
        exit(1)

    print(f"\n{Colors.BOLD}Files to be merged (in order of {sort_by}):{Colors.END}")
    for idx, (filename, creation_date) in enumerate(video_files, 1):
        print(
            f"{idx}. {filename} (Created: {creation_date.strftime('%Y-%m-%d %H:%M:%S')})"
        )

    with tempfile.NamedTemporaryFile(mode="w+", delete=True) as temp_file:
        # Write files in sorted order
        for filename, _ in video_files:
            temp_file.write(f"file '{os.path.join(input_dir, filename)}'\n")
        temp_file.flush()

        ffmpeg_cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-c:v", "hevc_videotoolbox",
            "-preset", "slow",
            "-movflags", "faststart",
            "-tag:v", "hvc1",
            "-b:v", "75M",
            "-maxrate", "100M",
            "-bufsize", "150M",
            "-i", temp_file.name,
            "-vf", f"scale={target_width}:{target_height}",
            "-r", str(fps),
        ]

        if enable_hdr:
            ffmpeg_cmd.extend(
                [
                    "-pix_fmt", "p010le",
                    "-color_primaries", "bt2020",
                    "-color_trc", "arib-std-b67",
                    "-colorspace", "bt2020nc",
                    "-profile:v", "main10",
                ]
            )
        else:
            ffmpeg_cmd.extend(["-pix_fmt", "yuv420p", "-profile:v", "main"])

        ffmpeg_cmd.append(output_file)

        # Print the ffmpeg command with proper formatting
        print_command(ffmpeg_cmd)

        if dry_run:
            print(
                f"{Colors.YELLOW}Dry run enabled: ffmpeg command will not be executed.{Colors.END}"
            )
            return

        # Execute the ffmpeg command
        try:
            subprocess.run(ffmpeg_cmd, check=True)
            print(
                f"{Colors.GREEN}Successfully concatenated and encoded to {output_file}{Colors.END}"
            )
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}Error during ffmpeg execution: {e}{Colors.END}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Concatenate and encode video files (MOV/MP4) to HEVC."
    )
    parser.add_argument(
        "input_dir", help="Path to the directory containing video files"
    )
    parser.add_argument("output_file", help="Path to the output HEVC file")
    parser.add_argument("--hdr", action="store_true", help="Enable HDR encoding")
    parser.add_argument(
        "--resolution",
        choices=["480p", "720p", "1080p", "4K"],
        default="4K",
        help="Output resolution (default: 4K)",
    )
    parser.add_argument(
        "--fps", type=int, default=30, help="Output frame rate (default: 30)"
    )
    parser.add_argument(
        "--sort_by",
        choices=["filename", "creation_date"],
        default="filename",
        help="Sort input files by filename or creation date (default: filename)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview operations without executing the ffmpeg command",
    )
    args = parser.parse_args()

    concatenate_and_encode(
        args.input_dir,
        args.output_file,
        args.hdr,
        args.resolution,
        args.fps,
        args.sort_by,
        dry_run=args.dry_run,
    )
