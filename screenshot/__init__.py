#!/home/walkers/git/.venv/bin/python
from pathlib import Path
import subprocess
from subprocess import Popen
import sys
from tempfile import mkdtemp
import time
import traceback

from git import Repo

POST_SHOT_SLEEP = 15


def notify_send(msg):
    Popen(
        f'notify-send "screenshot.py hit an exception" "{msg}" -a screenshot.py',
        shell=True,
    )


def notify_exception(type, value, tb) -> None:
    traceback_details = "\n".join(traceback.extract_tb(tb).format())

    msg = f"caller: {' '.join(sys.argv)}\n{type}: {value}\n{traceback_details}"
    print(msg)
    notify_send(msg)


sys.excepthook = notify_exception


def main() -> None:
    output_dir = Path(__file__).parents[1] / "static"
    output_dir.mkdir(exist_ok=True)
    name_proc = subprocess.Popen(
        'zenity --entry --text="filename"', shell=True, stdout=subprocess.PIPE
    )
    name_proc.wait()
    name = name_proc.stdout.read().decode().strip().lower().replace(" ", "-")
    if name == "":
        return

    shot_dir = mkdtemp()
    proc = subprocess.Popen(
        f'flameshot gui -p "{shot_dir}"',
        shell=True,
        stdout=subprocess.PIPE,
    )

    proc.wait()

    # even though flameshot was done, the file was only written about half the time.
    for _ in range(POST_SHOT_SLEEP):
        print(".", end="")
        time.sleep(1)
    print()

    images = Path(shot_dir).glob("*")
    temp_image = next(images)
    named_temp_image = Path(shot_dir) / f"{name}.png"
    output_image = output_dir / f"{name}.webp"
    temp_image.rename(named_temp_image)

    squoosh_cmd = f"""npx @squoosh/cli --webp '{{"quality":70,"target_size":0,"target_PSNR":0,"method":4,"sns_strength":50,"filter_strength":60,"filter_sharpness":0,"filter_type":1,"partitions":0,"segments":4,"pass":1,"show_compressed":0,"preprocessing":0,"autofilter":0,"partition_limit":0,"alpha_compression":1,"alpha_filtering":1,"alpha_quality":100,"lossless":0,"exact":0,"image_hint":0,"emulate_jpeg_size":0,"thread_level":0,"low_memory":0,"near_lossless":100,"use_delta_palette":0,"use_sharp_yuv":0}}' {named_temp_image} -d {output_dir}"""
    squoosh_proc = subprocess.Popen(squoosh_cmd, shell=True)
    squoosh_proc.wait()

    repo = Repo(Path(__file__).parents[1])

    if repo.git.diff(cached=True) != "":
        # handle staged files
        ...

    repo.git.add(output_image)
    repo.git.commit(message=f"NEW SHOT: {name}")
    repo.git.push()
    notify_send(f"successful push {name}")
