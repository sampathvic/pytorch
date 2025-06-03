import argparse
import io
import json
import os
from pathlib import Path
import shutil
from typing import List
from urllib.request import urlopen, Request
import zipfile

import requests



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
    )
    parser.add_argument("--mode", choices=["apply-changes", "format-input"], required=True, help="Mode of operation: 'apply-changes' to apply changes or 'format-input' to format input files.")
    parser.add_argument("--input-file", help="Path to the input file containing commit changes.")
    parser.add_argument("--cwd", type=str, default=str(Path.cwd()), help="Current working directory to use for relative paths in input file.")
    parser.add_argument("--workflow-id", type=str, default="commit_changes", help="Workflow ID to use for the commit changes. Default is 'commit_changes'.")
    return parser.parse_args()


def read_file(file_path: str) -> List[dict]:
    """Read the content of a file."""
    ret = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                change = json.loads(line)
                ret.append(change)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from line: {line}. Error: {e}")
    return ret

def download_artifacts(workflow_id: str) -> List[str]:
    tmp = Path("/tmp/lintrunner_artifacts") / workflow_id
    tmp.mkdir(parents=True, exist_ok=True)

    url = f"https://api.github.com/repos/pytorch/pytorch/actions/runs/{workflow_id}/artifacts"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN', '')}",
    }
    extracted_locations = []
    artifacts = requests.get(url, headers=headers).json()
    for artifact in artifacts['artifacts']:
        url = artifact["archive_download_url"]
        name = artifact["name"]
        location = requests.get(url, headers=headers).url
        artifact_binary = requests.get(location).content
        # unzip the binary
        with open(tmp / name, 'wb') as f:
            f.write(artifact_binary)
        extracted_to = tmp / f"{name}_extracted"
        with zipfile.ZipFile(tmp / name, 'r') as zip_ref:
            zip_ref.extractall(tmp / extracted_to)
        extracted_locations.append(str(extracted_to))
    return extracted_locations

def format_input_file(input_file: str, cwd: str) -> List[dict]:
    """Format the input file by ensuring all paths are relative to the current working directory."""
    all_changes = []
    for change in read_file(input_file):
        path = Path( change["path"])
        if  path.is_absolute():
            path = path.relative_to(Path(cwd))
        change["path"] = str(path)

    return all_changes

def apply_change(change: dict, cwd: str) -> None:
    """Apply a single change to the file system."""
    path = Path(change["path"])
    abs_path = Path(cwd) / path

    if "original" not in change or "replacement" not in change:
        print(f"Skipping change for {abs_path} as it does not have 'original' or 'replacement'.")
        return

    with open(abs_path, 'r') as f:
        original_content = f.read()
    if original_content != change["original"]:
        print(f"Skipping change for {abs_path} as the original content does not match the file content.")
        return
    with open(abs_path, 'w') as f:
        f.write(change["replacement"])
    print(f"Applied change to {abs_path}.")

def main() -> None:
    args = parse_args()

    if args.mode  == "format-input":
        formatted_changes = format_input_file(args.input_file, args.cwd)
        output_file = args.input_file + ".formatted"
        with open(output_file, 'w') as f:
            for change in formatted_changes:
                f.write(json.dumps(change) + "\n")
        print(f"Formatted changes written to {output_file}.")
        return


    # if args.mode == "apply-changes":

    res = download_artifacts(args.workflow_id)
    for location in res:
        print(f"Downloaded and extracted artifacts to: {location}")
        for file in Path(location).glob("**/*.formatted"):
            all_changes = format_input_file(file, args.cwd)
            for change in all_changes:
                apply_change(change, args.cwd)

    for path in res:
        print(f"Cleaning up temporary files at {path}")
        shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    main()
