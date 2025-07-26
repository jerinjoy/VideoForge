#!/usr/bin/env python3

import argparse
import subprocess
import os
import tempfile
import sys
from typing import Optional, Tuple

def check_mkvtoolnix_installed() -> None:
    """Check if required mkvtoolnix commands are available."""
    for cmd in ['mkvmerge', 'mkvpropedit', 'mkvinfo']:
        if not any(os.path.exists(os.path.join(path, cmd))
                  for path in os.environ["PATH"].split(os.pathsep)):
            print(f"Error: {cmd} is not installed. Please install mkvtoolnix first.")
            sys.exit(1)

def run_command(cmd: list[str], check: bool = True) -> Tuple[str, str]:
    """Run a command and return stdout and stderr."""
    try:
        result = subprocess.run(
            cmd,
            check=check,
            text=True,
            capture_output=True
        )
        return result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(cmd)}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)

class Track:
    def __init__(self, track_id: str, track_type: str, language: str, codec: str):
        self.track_id = track_id
        self.type = track_type
        self.language = language
        self.codec = codec

    def __str__(self):
        return f"Track ID {self.track_id}: {self.type} ({self.language}) [{self.codec}]"

def parse_tracks(mkv_file: str) -> list[Track]:
    """Parse track information from mkvinfo output."""
    stdout, _ = run_command(['mkvinfo', mkv_file])

    tracks = []
    current_track = {'track_id': '', 'track_type': '', 'language': 'undefined', 'codec': ''}

    for line in stdout.split('\n'):
        line = line.strip()
        if '|  + Track number:' in line:
            if current_track['track_id']:
                tracks.append(Track(**current_track))
                current_track = {'track_id': '', 'track_type': '', 'language': 'undefined', 'codec': ''}
            # Extract track ID from format: "Track number: 1 (track ID for mkvmerge & mkvextract: 0)"
            track_id_match = line.split('mkvextract:')[1].strip()
            current_track['track_id'] = track_id_match.rstrip(')')
        elif '|  + Track type:' in line:
            current_track['track_type'] = line.split(':')[1].strip()
        elif '|  + Codec ID:' in line:
            current_track['codec'] = line.split(':')[1].strip()
        elif '|  + Language:' in line and 'IETF' not in line:
            current_track['language'] = line.split(':')[1].strip()

    if current_track['track_id']:
        tracks.append(Track(**current_track))

    return tracks

def process_mkv_file(file: str, delete_subtitles: bool, keep_language: Optional[str], dry_run: bool) -> None:
    """Process an MKV file according to specified options."""
    if not os.path.exists(file):
        print(f"File '{file}' not found.")
        return

    print(f"Tracks in '{file}':")
    print("-" * 40)

    tracks = parse_tracks(file)
    for track in tracks:
        print(track)
    print("-" * 40)

    # Process audio tracks if keep_language is specified
    if keep_language:
        print(f"Analyzing audio tracks in '{file}'...")
        audio_tracks = [t for t in tracks if t.type == 'audio']
        target_tracks = [t for t in audio_tracks if t.language == keep_language]
        non_target_tracks = [t for t in audio_tracks if t.language != keep_language]

        # Show which tracks will be kept/removed
        for track in target_tracks:
            print(f"Found {keep_language} audio track (ID: {track.track_id}) - will keep")
        for track in non_target_tracks:
            print(f"Found non-{keep_language} audio track (ID: {track.track_id}) - will be removed")

        # Only process if there are non-target language tracks to remove
        if non_target_tracks:
            if not target_tracks:
                print(f"Warning: No {keep_language} audio tracks found. Keeping all audio tracks.")
            else:
                audio_track_ids = ','.join(t.track_id for t in target_tracks)
                if dry_run:
                    print(f"Would keep only {keep_language} audio tracks in '{file}'.")
                else:
                    temp_file = f"{os.path.splitext(file)[0]}_{keep_language}.mkv"
                    cmd = ['mkvmerge', '-o', temp_file, '--video-tracks', '0',
                          '--audio-tracks', audio_track_ids, file]
                    run_command(cmd)

                    # Check output file size
                    original_size = os.path.getsize(file)
                    new_size = os.path.getsize(temp_file)

                    if new_size > original_size / 2:
                        os.replace(temp_file, file)
                        print(f"Kept only {keep_language} audio tracks in '{file}'.")
                    else:
                        print("Error: Output file is suspiciously small. Operation aborted.")
                        os.remove(temp_file)
                        sys.exit(1)
        else:
            print("No audio track changes needed.")

    # Process subtitles if requested
    if delete_subtitles:
        subtitle_tracks = [t for t in tracks if t.type == 'subtitles']
        if not subtitle_tracks:
            print(f"No subtitles found in '{file}'.")
        else:
            print(f"Subtitles found in '{file}'.")
            if dry_run:
                print(f"Would remove all subtitles from '{file}'.")
            else:
                temp_file = f"{os.path.splitext(file)[0]}_no_subtitles.mkv"
                run_command(['mkvmerge', '-o', temp_file, '--no-subtitles', file])
                os.replace(temp_file, file)
                print(f"All subtitles removed from '{file}'.")

    # Update title if needed
    title = os.path.splitext(os.path.basename(file))[0]
    stdout, _ = run_command(['mkvinfo', file])
    current_title = None
    for line in stdout.split('\n'):
        if '|  + Title:' in line:
            current_title = line.split(':')[1].strip()
            break

    if current_title != title:
        if dry_run:
            print(f"Would set the title of '{file}' to '{title}'.")
        else:
            run_command(['mkvpropedit', file, '--edit', 'info', '--set', f'title={title}'])
            print(f"Set the title of '{file}' to '{title}'.")
    else:
        print(f"The title of '{file}' already matches the filename. No change needed.")

    print()

def main():
    parser = argparse.ArgumentParser(description='Process MKV files.')
    parser.add_argument('file', help='MKV file to process', nargs='?')
    parser.add_argument('--keep-language', help='Keep only audio tracks in specified language (ISO 639-3 code)')
    parser.add_argument('--delete-subtitles', action='store_true', help='Remove subtitle tracks')
    parser.add_argument('--dry-run', action='store_true', help='Simulate actions without making changes')

    args = parser.parse_args()

    if not args.file:
        parser.print_help()
        sys.exit(0)

    check_mkvtoolnix_installed()

    if not args.file.endswith('.mkv'):
        print(f"'{args.file}' is not an MKV file.")
        sys.exit(1)

    process_mkv_file(args.file, args.delete_subtitles, args.keep_language, args.dry_run)

if __name__ == '__main__':
    main()