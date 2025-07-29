#!/usr/bin/env fish

function get_file_size
    set file $argv[1]
    if test -f "$file"
        stat -f %z "$file" 2>/dev/null
    end
end

function download_with_size_check --argument url target_dir
    set filename (basename "$url")
    set target_file "$target_dir/$filename"

    # Get remote size
    set remote_size (curl -sI "$url" | grep -i '^Content-Length:' | awk '{print $2}' | string trim)

    if test -z "$remote_size"
        echo "⚠️  Could not determine remote size for $filename. Downloading anyway."
        wget --show-progress --progress=bar:force:noscroll --directory-prefix="$target_dir" "$url"
        return
    end

    set local_size (get_file_size "$target_file")

    if test "$local_size" = "$remote_size"
        echo "✅ Skipping $filename (already downloaded, size: $local_size bytes)"
        return
    else if test -n "$local_size"
        echo "🔁 Redownloading $filename (local: $local_size, remote: $remote_size)"
    else
        echo "⬇️  Downloading $filename (remote size: $remote_size bytes)"
    end

    wget --show-progress --progress=bar:force:noscroll --directory-prefix="$target_dir" "$url"
end

function download_urls
    if test (count $argv) -lt 2
        echo "Usage: download_urls.fish <target_dir> <file1.txt> [file2.txt ...]"
        return 1
    end

    set target_dir $argv[1]
    set url_files $argv[2..-1]

    mkdir -p "$target_dir"

    for file in $url_files
        if not test -f "$file"
            echo "⚠️  File not found: $file"
            continue
        end

        for url in (string trim < "$file" | string split '\n')
            if test -z "$url"; or string match -qr '^#' -- "$url"
                continue
            end

            download_with_size_check "$url" "$target_dir"
        end
    end
end

download_urls $argv

