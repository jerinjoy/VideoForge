#!/bin/bash

# Script to process MKV files.
# Removes unnecessary parts of the file.
# Written with Perplexity.ai

# Exit immediately if a command exits with a non-zero status
set -e

# Function to display help message
show_help() {
	echo "Usage: $0 [--delete-subtitles] <mkv-file>"
	echo
	echo "Options:"
	echo "  --delete-subtitles  Remove subtitle tracks from the MKV file."
	echo "  --help              Display this help message."
	exit 0
}

# Function to check if mkvtoolnix is installed
check_mkvtoolnix_installed() {
	if ! command -v mkvmerge &>/dev/null || ! command -v mkvpropedit &>/dev/null; then
		echo "mkvtoolnix is not installed. Please install it first."
		exit 1
	fi
}

# Function to remove attachments and optionally subtitles from an MKV file
remove_attachments_and_subtitles() {
	local file="$1"
	local delete_subtitles="$2"

	# Check for attachments
	attachments=$(mkvmerge -i "$file" | grep 'Attachment ID' || true)

	if [ -z "$attachments" ]; then
		echo "No attachments found in '$file'."
	else
		echo "Attachments found in '$file'. Removing them..."

		# Extract attachment IDs, sort them in descending order, and remove them
		attachment_ids=$(echo "$attachments" | awk '{print $3}' | sed 's/://g' | sort -nr)

		for id in $attachment_ids; do
			mkvpropedit "$file" --delete-attachment "$id"
			echo "Removed attachment ID $id from '$file'."
		done
	fi

	# Check and remove subtitle tracks if the flag is set
	if [ "$delete_subtitles" = true ]; then
		subtitle_tracks=$(mkvmerge -i "$file" | grep 'subtitles' || true)

		if [ -z "$subtitle_tracks" ]; then
			echo "No subtitles found in '$file'."
		else
			echo "Subtitles found in '$file'. Removing them..."

			# Create a new file without subtitle tracks
			temp_file="${file%.mkv}_no_subtitles.mkv"
			mkvmerge -o "$temp_file" --no-subtitles "$file"

			# Replace the original file with the new one
			mv "$temp_file" "$file"

			echo "All subtitles removed from '$file'."
		fi
	fi

	echo "All attachments removed from '$file'."
}

# Main script
main() {
	check_mkvtoolnix_installed

	if [ $# -eq 0 ]; then
		show_help
	fi

	delete_subtitles=false

	# Parse options
	while [[ $# -gt 0 ]]; do
		case "$1" in
		--delete-subtitles)
			delete_subtitles=true
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
		remove_attachments_and_subtitles "$file" "$delete_subtitles"
	else
		echo "File '$file' not found."
		exit 1
	fi
}

# Execute the main function with all script arguments
main "$@"
