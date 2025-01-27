#!/bin/zsh

# Script to process MKV files.
# Removes unnecessary parts of the file.
# Written with Perplexity.ai

# Exit immediately if a command exits with a non-zero status
set -e

# Function to display help message
show_help() {
    echo "Usage: $0 [--keep-language LANG] [--delete-subtitles] [--dry-run]"
    echo
    echo "Options:"
    echo "  --keep-language LANG  Keep only audio tracks in the specified language (use ISO 639-3 code, e.g., 'mal' for Malayalam)"
    echo "  --delete-subtitles    Remove subtitle tracks from the MKV file"
    echo "  --dry-run            Simulate the actions without making any changes"
    echo "  --help               Display this help message"
    exit 0
}

# Function to check if mkvtoolnix is installed
check_mkvtoolnix_installed() {
	if ! command -v mkvmerge &>/dev/null || ! command -v mkvpropedit &>/dev/null; then
		echo "mkvtoolnix is not installed. Please install it first."
		exit 1
	fi
}

# Function to remove attachments, optionally subtitles, and set the title
process_mkv_file() {
    local file="$1"
    local delete_subtitles="$2"
    local keep_language="$3"
    local dry_run="$4"
    local title="${file%.mkv}"
    local needs_audio_processing=false
    local audio_tracks_to_keep=""
    local found_target_language=false

    # List all tracks in the file
    echo "Tracks in '$file':"
    echo "----------------------------------------"

    # Store track information in temporary files
    local tmpfile=$(mktemp)
    mkvinfo "$file" > "$tmpfile"

    # First pass: display track information
    local current_id=""
    local current_type=""
    local current_lang=""
    local current_codec=""

    while IFS= read -r line; do
        if [[ $line == *"Track number:"* ]]; then
            if [ ! -z "$current_id" ]; then
                echo "Track ID $current_id: $current_type ($current_lang) [$current_codec]"
            fi
            current_id=$(echo "$line" | grep -o "mkvextract: [0-9]*" | awk '{print $2}')
            current_lang="undefined"
        elif [[ $line == *"Track type:"* ]]; then
            current_type=$(echo "$line" | cut -d: -f2 | tr -d ' ')
        elif [[ $line == *"Codec ID:"* ]]; then
            current_codec=$(echo "$line" | cut -d: -f2 | tr -d ' ')
        elif [[ $line == *"Language:"* ]] && [[ $line != *"Language (IETF"* ]]; then
            current_lang=$(echo "$line" | cut -d: -f2 | tr -d ' ')
        fi
    done < "$tmpfile"
    # Print last track if exists
    if [ ! -z "$current_id" ]; then
        echo "Track ID $current_id: $current_type ($current_lang) [$current_codec]"
    fi

    echo "----------------------------------------"

    # Process audio tracks if keep_language is specified
    if [ ! -z "$keep_language" ]; then
        echo "Analyzing audio tracks in '$file'..."

        # Second pass: process audio tracks
        current_id=""
        current_type=""
        current_lang=""
        audio_tracks_to_keep=""
        found_target_language=false

        while IFS= read -r line; do
            if [[ $line == *"Track number:"* ]]; then
                if [ "$current_type" = "audio" ]; then
                    if [ "$current_lang" = "$keep_language" ]; then
                        # Append track ID to the list of tracks to keep
                        if [ -z "$audio_tracks_to_keep" ]; then
                            audio_tracks_to_keep="$current_id"
                        else
                            audio_tracks_to_keep="$audio_tracks_to_keep,$current_id"
                        fi
                        found_target_language=true
                        echo "Found $keep_language audio track (ID: $current_id) - will keep"
                    else
                        echo "Found non-$keep_language audio track (ID: $current_id) - will be removed"
                        needs_audio_processing=true
                    fi
                fi
                current_id=$(echo "$line" | grep -o "mkvextract: [0-9]*" | awk '{print $2}')
            elif [[ $line == *"Track type:"* ]]; then
                current_type=$(echo "$line" | cut -d: -f2 | tr -d ' ')
            elif [[ $line == *"Language:"* ]] && [[ $line != *"Language (IETF"* ]]; then
                current_lang=$(echo "$line" | cut -d: -f2 | tr -d ' ')
            fi
        done < "$tmpfile"

        # Process last track if it's audio
        if [ "$current_type" = "audio" ]; then
            if [ "$current_lang" = "$keep_language" ]; then
                if [ -z "$audio_tracks_to_keep" ]; then
                    audio_tracks_to_keep="$current_id"
                else
                    audio_tracks_to_keep="$audio_tracks_to_keep,$current_id"
                fi
                found_target_language=true
                echo "Found $keep_language audio track (ID: $current_id) - will keep"
            else
                echo "Found non-$keep_language audio track (ID: $current_id) - will be removed"
                needs_audio_processing=true
            fi
        fi

        rm "$tmpfile"

        if [ "$needs_audio_processing" = true ]; then
            if [ "$dry_run" = true ]; then
                echo "Would keep only $keep_language audio tracks in '$file'."
            else
                echo "Processing audio tracks..."
                temp_file="${file%.mkv}_${keep_language}.mkv"
                if [ "$found_target_language" = false ]; then
                    echo "Warning: No $keep_language audio tracks found. Keeping all audio tracks."
                else
                    # Construct the command using consistent --audio-tracks syntax
                    cmd="mkvmerge -o \"$temp_file\" --video-tracks 0 --audio-tracks $audio_tracks_to_keep \"$file\""
                    echo "Executing: $cmd"
                    eval "$cmd"
                    if [ $? -eq 0 ] && [ -s "$temp_file" ]; then
                        # Check if the output file is reasonable (at least 50% of original size)
                        original_size=$(stat -f %z "$file")
                        new_size=$(stat -f %z "$temp_file")
                        if [ $new_size -gt $((original_size / 2)) ]; then
                            mv "$temp_file" "$file"
                            echo "Kept only $keep_language audio tracks in '$file'."
                        else
                            echo "Error: Output file is suspiciously small. Operation aborted."
                            rm "$temp_file"
                            exit 1
                        fi
                    else
                        echo "Error: mkvmerge failed or output file is empty"
                        [ -f "$temp_file" ] && rm "$temp_file"
                        exit 1
                    fi
                fi
            fi
        else
            echo "No audio track changes needed."
        fi
    fi

	# Check and remove subtitle tracks if the flag is set
	if [ "$delete_subtitles" = true ]; then
		subtitle_tracks=$(mkvmerge -i "$file" | grep 'subtitles' || true)

		if [ -z "$subtitle_tracks" ]; then
			echo "No subtitles found in '$file'."
		else
			echo "Subtitles found in '$file'."

			if [ "$dry_run" = true ]; then
				echo "Would remove all subtitles from '$file'."
			else
				# Create a new file without subtitle tracks
				temp_file="${file%.mkv}_no_subtitles.mkv"
				mkvmerge -o "$temp_file" --no-subtitles "$file"

				# Replace the original file with the new one
				mv "$temp_file" "$file"

				echo "All subtitles removed from '$file'."
			fi
		fi
	fi

	# Get the current title
	current_title=$(mkvinfo "$file" | grep 'Title' | awk -F: '{print $2}' | xargs)

	# Update the title if it doesn't match the filename
	if [ "$current_title" != "$title" ]; then
		if [ "$dry_run" = true ]; then
			echo "Would set the title of '$file' to '$title'."
		else
			mkvpropedit "$file" --edit info --set "title=$title"
			echo "Set the title of '$file' to '$title'."
		fi
	else
		echo "The title of '$file' already matches the filename. No change needed."
	fi

	echo ""
}

# Main script
main() {
    check_mkvtoolnix_installed

    if [ $# -eq 0 ]; then
        show_help
    fi

    delete_subtitles=false
    keep_language=""
    dry_run=false

    # Parse options
    while [[ $# -gt 0 ]]; do
        case "$1" in
        --keep-language)
            shift
            keep_language="$1"
            shift
            ;;
        --delete-subtitles)
            delete_subtitles=true
            shift
            ;;
        --dry-run)
            dry_run=true
            shift
            ;;
        --help)
            show_help
            ;;
        *)
            if [[ "$1" == *.mkv ]]; then
                file="$1"
                shift
            else
                echo "'$1' is not an MKV file."
                exit 1
            fi
            ;;
        esac
    done

    if [ -z "$file" ]; then
        echo "No MKV file specified."
        show_help
    fi

    if [ -f "$file" ]; then
        process_mkv_file "$file" "$delete_subtitles" "$keep_language" "$dry_run"
    else
        echo "File '$file' not found."
        exit 1
    fi
}


# Execute the main function with all script arguments
main "$@"
