#!/bin/bash

# Script to process MKV files.
# Removes unnecessary parts of the file.

# Function to check if mkvtoolnix is installed
check_mkvtoolnix_installed() {
	if ! command -v mkvpropedit &>/dev/null; then
		echo "mkvtoolnix is not installed. Please install it first."
		exit 1
	fi
}

# Function to remove attachments from an MKV file
remove_attachments() {
	local file="$1"

	# Check for attachments
	attachments=$(mkvmerge -i "$file" | grep 'Attachment ID')

	if [ -z "$attachments" ]; then
		echo "No attachments found in '$file'."
	else
		echo "Attachments found in '$file'. Removing them..."

		# Extract attachment IDs and remove them
		attachment_ids=$(echo "$attachments" | awk '{print $3}')

		for id in $attachment_ids; do
			# Remove trailing colon from the ID
			id=${id%:}
			mkvpropedit "$file" --delete-attachment "$id"
			echo "Removed attachment ID $id from '$file'."
		done

		echo "All attachments removed from '$file'."
	fi
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
				remove_attachments "$file"
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
