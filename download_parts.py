#!/usr/bin/env python3
"""Multi-part file downloader for fuckingfast.co (Cloudflare-protected)."""

import os
import sys
import time
import re
import json
import urllib.request
import urllib.error
import urllib.parse

try:
    import cloudscraper # type: ignore
except ImportError:
    cloudscraper = None


def format_size(num_bytes):
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def format_time(seconds):
    if seconds < 60:
        return f"{seconds:.0f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s"


def get_filename_from_url(url, index):
    # Check fragment first — fuckingfast.co encodes the filename after '#'
    parsed = urllib.parse.urlparse(url)
    fragment = parsed.fragment.strip()
    if fragment:
        # The fragment is the filename hint, e.g. "God_of_War_--_..._part01.rar"
        # Grab just the last component (after last underscore-dot sequence or as-is)
        candidate = os.path.basename(fragment.replace("_--_", "/"))
        # Fall back to raw fragment if basename strips too much
        if not candidate or "." not in candidate:
            candidate = fragment.split(".")[-2] + "." + fragment.split(".")[-1] if "." in fragment else ""
        if candidate and "." in candidate:
            return candidate
    path = parsed.path
    name = os.path.basename(path)
    if name and "." in name:
        return name
    return f"part_{index + 1:03d}.bin"


def make_progress_hook(filename, file_index, total_files):
    start_time = [None]

    def hook(block_count, block_size, total_size):
        if start_time[0] is None:
            start_time[0] = time.time()
        downloaded = block_count * block_size
        elapsed = time.time() - start_time[0]
        if total_size > 0:
            downloaded = min(downloaded, total_size)
            pct = downloaded / total_size * 100
            bar_filled = int(pct / 2)
            bar = "#" * bar_filled + "-" * (50 - bar_filled)
            speed = downloaded / elapsed if elapsed > 0 else 0
            remaining = (total_size - downloaded) / speed if speed > 0 else 0
            size_info = f"{format_size(downloaded)}/{format_size(total_size)}"
            eta = f"ETA {format_time(remaining)}"
            line = (f"\r  [{bar}] {pct:5.1f}%  {size_info}  "
                    f"{format_size(speed)}/s  {eta}   ")
        else:
            speed = downloaded / elapsed if elapsed > 0 else 0
            line = (f"\r  Downloading... {format_size(downloaded)}  "
                    f"{format_size(speed)}/s   ")
        sys.stdout.write(line)
        sys.stdout.flush()

    return hook


def resolve_download_url(url, max_retries=5):
    """Use cloudscraper to bypass Cloudflare, POST to /go, and return
    (real_download_url, suggested_filename)."""
    if cloudscraper is None:
        raise RuntimeError("cloudscraper not installed (pip install cloudscraper)")
    last_err = None
    for attempt in range(max_retries):
        try:
            s = cloudscraper.create_scraper()
            r = s.get(url)
            if r.status_code != 200:
                last_err = RuntimeError(f"Page fetch failed: HTTP {r.status_code}")
                time.sleep(2 + attempt * 2)
                continue
            fname_hint = None
            m_fn = re.search(r'<span[^>]*>([^<]+\.(?:rar|bin|zip|7z|iso))</span>', r.text, re.I)
            if m_fn:
                fname_hint = m_fn.group(1).strip()
            m = re.search(r'(/f/[a-z0-9]+/go)', r.text)
            if not m:
                last_err = RuntimeError("Could not find download trigger on page")
                time.sleep(2 + attempt * 2)
                continue
            go_url = "https://fuckingfast.co" + m.group(1)
            r2 = s.post(go_url, data={}, headers={
                "HX-Request": "true",
                "Referer": url,
            })
            dl = r2.headers.get("Hx-Redirect") or r2.headers.get("Location")
            if not dl:
                last_err = RuntimeError(f"No redirect returned (status {r2.status_code})")
                time.sleep(2 + attempt * 2)
                continue
            try:
                r3 = s.head(dl, allow_redirects=True, timeout=10)
                cd = r3.headers.get("Content-Disposition", "")
                m_cd = re.search(r"filename\*?=(?:UTF-8''|\"?)([^\";]+)", cd, re.I)
                if m_cd:
                    fname_hint = urllib.parse.unquote(m_cd.group(1).strip().strip('"'))
            except Exception:
                pass
            return dl, fname_hint
        except Exception as exc:
            last_err = exc
            time.sleep(2 + attempt * 2)
    raise RuntimeError(f"Failed after {max_retries} attempts: {last_err}")


def download_file(url, dest_dir, file_index, total_files):
    fallback_name = get_filename_from_url(url, file_index)
    print(f"\n[{file_index + 1}/{total_files}] Resolving...")
    print(f"  URL : {url}")
    try:
        real_url, fname_hint = resolve_download_url(url)
        filename = fname_hint if fname_hint else fallback_name
        dest_path = os.path.join(dest_dir, filename)
        base, ext = os.path.splitext(dest_path)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = f"{base}_{counter}{ext}"
            counter += 1
        print(f"  File: {os.path.basename(dest_path)}")
        print(f"  Resolved -> {real_url[:90]}...")
        hook = make_progress_hook(os.path.basename(dest_path), file_index, total_files)
        urllib.request.urlretrieve(real_url, dest_path, reporthook=hook)
        sys.stdout.write("\n")
        size = os.path.getsize(dest_path)
        print(f"  Saved  ->  {dest_path}  ({format_size(size)})")
        return True
    except urllib.error.HTTPError as exc:
        sys.stdout.write("\n")
        print(f"  HTTP error {exc.code}: {exc.reason}")
    except urllib.error.URLError as exc:
        sys.stdout.write("\n")
        print(f"  URL error: {exc.reason}")
    except Exception as exc:
        sys.stdout.write("\n")
        print(f"  Unexpected error: {exc}")
    return False


def collect_links():
    print("\nPaste your download links below - one per line.\n"
          "Press Enter on a blank line when you're done:\n")
    links = []
    while True:
        try:
            line = input("  Link: ").strip()
        except EOFError:
            break
        if not line:
            if links:
                break
            print("  (No links entered yet - paste at least one.)")
            continue
        links.append(line)
    return links


def main():
    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    if not os.path.isdir(downloads_dir):
        print(f"Could not find Downloads folder at: {downloads_dir}")
        downloads_dir = os.getcwd()
        print(f"Using current directory instead: {downloads_dir}")

    if cloudscraper is None:
        print("\nERROR: 'cloudscraper' is not installed.")
        print("Run:  pip install cloudscraper")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("        Multi-Part File Downloader")
    print("=" * 50)
    print(f"\nFiles will be saved inside:  {downloads_dir}\\<folder name>")

    while True:
        folder_name = input("\nEnter a name for the download folder: ").strip()
        invalid = r'\/:*?"<>|'
        cleaned = "".join(c for c in folder_name if c not in invalid)
        if cleaned != folder_name:
            print(f"  Invalid characters removed - using: '{cleaned}'")
            folder_name = cleaned
        if folder_name:
            break
        print("  Folder name cannot be empty. Please try again.")

    dest_dir = os.path.join(downloads_dir, folder_name)
    os.makedirs(dest_dir, exist_ok=True)
    print(f"\n  Folder ready: {dest_dir}")

    links = collect_links()
    if not links:
        print("\nNo links provided. Exiting.")
        sys.exit(0)

    print(f"\n  {len(links)} link(s) collected. Starting downloads...")
    print("-" * 50)

    success_count = 0
    failed = []

    for i, url in enumerate(links):
        ok = download_file(url, dest_dir, i, len(links))
        if ok:
            success_count += 1
        else:
            failed.append((i + 1, url))

    print("\n" + "=" * 50)
    print(f"  Done!  {success_count}/{len(links)} file(s) downloaded successfully.")
    print(f"  Saved to: {dest_dir}")
    if failed:
        print(f"\n  {len(failed)} file(s) failed:")
        for num, url in failed:
            print(f"     [{num}] {url}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted by user. Goodbye!")
        sys.exit(1)