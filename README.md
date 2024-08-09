# Video Forge

Collection of scripts I use to work with video files.

## hevc_stitcher.py

Script to merge video files and encode them as HEVC.

```shell
❯ ./hevc_stitcher.py --help
usage: hevc_stitcher.py [-h] [--hdr] [--resolution {480p,720p,1080p,4K}] [--fps FPS] [--sort_by {filename,creation_date}] [--dry-run] input_dir output_file

Concatenate and encode video files (MOV/MP4) to HEVC.

positional arguments:
  input_dir             Path to the directory containing video files
  output_file           Path to the output HEVC file

optional arguments:
  -h, --help            show this help message and exit
  --hdr                 Enable HDR encoding
  --resolution {480p,720p,1080p,4K}
                        Output resolution (default: 4K)
  --fps FPS             Output frame rate (default: 30)
  --sort_by {filename,creation_date}
                        Sort input files by filename or creation date (default: filename)
  --dry-run             Preview operations without executing the ffmpeg command
```

## process_mkv

Script to process MKV files.

```shell
for file in *.mkv; if test -f "$file"; ~/workspace/process_mkv/process_mkv.sh --delete-subtitles  "$file"; end; end
```
