#!/usr/bin/env python3
"""Fetch the latest AlexxIT/go2rtc release and rewrite Formula/go2rtc.rb."""

import hashlib
import json
import os
import sys
import textwrap
import urllib.request

UPSTREAM_REPO = "AlexxIT/go2rtc"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FORMULA_PATH = os.path.join(SCRIPT_DIR, "..", "..", "Formula", "go2rtc.rb")

EXPECTED_ASSETS = {
    "arm64": "go2rtc_mac_arm64.zip",
    "amd64": "go2rtc_mac_amd64.zip",
}


def api_request(url):
    """Make an authenticated GitHub API request."""
    req = urllib.request.Request(url)
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def download_bytes(url):
    """Download raw bytes from a URL."""
    req = urllib.request.Request(url)
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"token {token}")
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def sha256_of_bytes(data):
    return hashlib.sha256(data).hexdigest()


def parse_checksums_file(text):
    """Parse a BSD- or GNU-style checksums file into {filename: sha256}."""
    result = {}
    for line in text.strip().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            sha = parts[0]
            filename = parts[-1].lstrip("*")
            if len(sha) == 64:
                result[filename] = sha
    return result


def resolve_sha256(release, asset_name):
    """Get SHA-256 for an asset: try a checksums file first, then download."""
    # Look for a checksums asset in the release
    for asset in release.get("assets", []):
        name_lower = asset["name"].lower()
        if "checksum" in name_lower or "sha256" in name_lower:
            print(f"  Found checksums asset: {asset['name']}")
            data = download_bytes(asset["browser_download_url"])
            checksums = parse_checksums_file(data.decode("utf-8", errors="replace"))
            if asset_name in checksums:
                print(f"  Using checksum from {asset['name']}")
                return checksums[asset_name]

    # Fall back to downloading the asset and computing locally
    print(f"  Downloading {asset_name} to compute SHA-256...")
    for asset in release["assets"]:
        if asset["name"] == asset_name:
            data = download_bytes(asset["browser_download_url"])
            return sha256_of_bytes(data)

    raise RuntimeError(f"Asset {asset_name} not found in release")


def write_formula(version, arm64_url, arm64_sha, amd64_url, amd64_sha):
    """Write the Homebrew formula file."""
    formula = textwrap.dedent(f"""\
        class Go2rtc < Formula
          desc "Camera streaming application with RTSP, WebRTC, HomeKit and FFmpeg support"
          homepage "https://github.com/AlexxIT/go2rtc"
          version "{version}"
          license "MIT"

          on_macos do
            on_arm do
              url "{arm64_url}"
              sha256 "{arm64_sha}"
            end
            on_intel do
              url "{amd64_url}"
              sha256 "{amd64_sha}"
            end
          end

          def install
            bin.install "go2rtc"
          end

          service do
            run [opt_bin/"go2rtc"]
            keep_alive true
            working_dir var/"go2rtc"
            log_path var/"log/go2rtc.log"
            error_log_path var/"log/go2rtc.log"
          end

          test do
            system bin/"go2rtc", "-version"
          end
        end
    """)
    os.makedirs(os.path.dirname(FORMULA_PATH), exist_ok=True)
    with open(FORMULA_PATH, "w") as f:
        f.write(formula)


def main():
    print(f"Fetching latest release for {UPSTREAM_REPO}...")
    release = api_request(
        f"https://api.github.com/repos/{UPSTREAM_REPO}/releases/latest"
    )
    tag = release["tag_name"]
    version = tag.lstrip("v")
    print(f"Latest release: {tag} (version {version})")

    # Locate required assets
    asset_urls = {}
    for arch, filename in EXPECTED_ASSETS.items():
        found = None
        for asset in release.get("assets", []):
            if asset["name"] == filename:
                found = asset
                break
        if found is None:
            print(f"ERROR: expected asset '{filename}' not found in release {tag}", file=sys.stderr)
            sys.exit(1)
        asset_urls[arch] = found["browser_download_url"]

    # Resolve SHA-256 checksums
    print("Resolving SHA-256 checksums...")
    arm64_sha = resolve_sha256(release, EXPECTED_ASSETS["arm64"])
    print(f"  arm64: {arm64_sha}")
    amd64_sha = resolve_sha256(release, EXPECTED_ASSETS["amd64"])
    print(f"  amd64: {amd64_sha}")

    if not arm64_sha or not amd64_sha:
        print("ERROR: could not determine SHA-256 for one or more assets", file=sys.stderr)
        sys.exit(1)

    # Write formula
    write_formula(version, asset_urls["arm64"], arm64_sha, asset_urls["amd64"], amd64_sha)
    print(f"Formula written to {FORMULA_PATH}")

    # Expose version for GitHub Actions
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"version={version}\n")


if __name__ == "__main__":
    main()
