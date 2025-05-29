import os
import subprocess
import json


"""
=== Requirements ===

- python (obviously)
- mkvmerge
- mkvpropedit

"""


# === Config ===
DRY_RUN = True          # Set to False to actually modify files
DIRECTORY = r"C:\path\to\your\directory"
FILE_EXTENSION = ".mkv"
DESIRED_SUBTITLE_TRACK_TITLE = ""
DESIRED_AUDIO_LANG = "jpn"


class Operations:
    SET = "set"
    UNSET = "unset"

class MkvMergeError(Exception):
    pass


# === Final Command Execution ===
def edit_tracks(filepath: str, tracks: list) -> None:
    for track in tracks:

        track_id = track["id"] + 1      # for some reason, we need to start counting at 1, not at 0
        operation = track.get("operation", "")
        type_ = track.get("type", "Unknown Track Type")

        if operation == "":
            continue

        params = [
            "mkvpropedit",
            filepath,
            "--edit",
            f"track:@{ track_id }",
            "--set",
            f"flag-default={ 1 if operation == Operations.SET else 0 }",
        ]

        if DRY_RUN:
            print("           Command:", " ".join(params))
            print(f"  [DRY RUN] Would { operation } default { type_ } (ID { track_id })")
        else:
            print(f"  ✔ Default { type_ } { operation } (ID { track_id })")
            subprocess.run(params)


def get_file_info(mkvmerge_output: dict) -> dict:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["mkvmerge", "--identify", "--identification-format", "json", filepath],
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
        encoding = "utf-8",
        errors = "replace",     # Replace invalid characters
        check = False           # Don't auto-raise errors
    )
    mkvmerge_output["result"] = result     # Temporary, for error output

    if result.returncode != 0 or not result.stdout:
        raise MkvMergeError()

    file_info = json.loads(result.stdout)

    if file_info["tracks"] is None:
        raise MkvMergeError()

    return file_info


def analyze_tracks(tracks: list) -> dict:
    result = {
        "audio": [],
        "subtitles": [],
    }
    audio_is_set: bool = False
    subtitle_is_set: bool = False

    for track in tracks:
        props = track.get("properties", {})
        type_ = track.get("type", "")

        if type_ == "audio":
            if props.get("language") == DESIRED_AUDIO_LANG and audio_is_set is False:
                track["operation"] = Operations.SET
                result["audio"].append(track)
                audio_is_set = True
            else:
                track["operation"] = Operations.UNSET
                result["subtitles"].append(track)

        elif type_ == "subtitles":
            if props.get("track_name", "") == DESIRED_SUBTITLE_TRACK_TITLE and subtitle_is_set is False:
                track["operation"] = Operations.SET
                result["subtitles"].append(track)
                subtitle_is_set = True
            else:
                track["operation"] = Operations.UNSET
                result["subtitles"].append(track)

    return result


# === Main script ===
for filename in os.listdir(DIRECTORY):
    if not filename.lower().endswith(FILE_EXTENSION):
        continue

    filepath: str = os.path.join(DIRECTORY, filename)
    print(f"\nProcessing: {filename}")


    error_output: dict = {}
    try:
        file_info: dict = get_file_info(error_output)
    except MkvMergeError:
        print(f"❌ mkvmerge failed for {filename}")
        if result := error_output.get("result"):
            print(result.stderr)
        continue
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON for {filename}: {e}")
        continue
    except Exception as e:
        print(f"❌ Error running mkvmerge on {filename}: {e}")
        continue

    tracks = file_info.get("tracks", [])
    analyze_tracks(tracks)

    edit_tracks(filepath, tracks)
