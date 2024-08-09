#!/bin/bash

# Script to process MKV files.
# Removes unnecessary parts of the file.
# Written with Perplexity.ai

# Function to check if mkvtoolnix is installed
check_mkvtoolnix_installed() {
	if ! command -v mkvmerge &>/dev/null || ! command -v mkvpropedit &>/dev/null; then
		echo "mkvtoolnix is not installed. Please install it first."
		exit 1
	fi
}

# Function to remove attachments and subtitles from an MKV file
remove_attachments_and_subtitles() {
	local file="$1"

	# Check for attachments
	attachments=$(mkvmerge -i "$file" | grep 'Attachment ID')

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

	# Check for subtitle tracks
	subtitle_tracks=$(mkvmerge -i "$file" | grep 'subtitles')

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

	echo "All attachments and subtitles removed from '$file'."
}

# Main script
main() {
	check_mkvtoolnix_installed

	if [ $# -eq 0 ]; then
		echo "Usage: $0 <mkv-file>"
		exit 1
	fi

	for file in "$@"; do
		if [[ "$file" == *.mkv ]]; then
			if [ -f "$file" ]; then
				remove_attachments_and_subtitles "$file"
			else
				echo "File '$file' not found."
			fi
		else
			echo "'$file' is not an MKV file."
		fi
	done
}

# Execute the main function with all script arguments
main "$@"
