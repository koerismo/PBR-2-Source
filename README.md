# PBR-2-Source
A Python-powered gui for converting pbr materials into Source Engine-compatible materials.

## Features
- Supports PNG, JPG, BMP, and TGA input.
- Automatically generates material VMTs.
- Generates out-of-the-box functional materials for both PBR and traditional shaders.
- Live material reloading with game integration.

---

*Demonstration of PBR-2-Source usage*

![PBR-2-Source_A8YT6MpP3v](https://github.com/user-attachments/assets/f6f09f18-ce38-49bc-9822-fb045e30b229)
 
---
### [View Builds](https://github.com/koerismo/PBR-2-Source/releases)

## Command-line Arguments

```
usage: PBR-2-Source.exe [-h] [--logfile LOGFILE] [--config CONFIG]

options:
  -h, --help         show this help message and exit
  --logfile LOGFILE  Writes errors and information to the specified file.
  --config CONFIG    Uses the specified config path instead of the installation config path
```


## Building from Source

### With uv

```
uv sync
uv run PyInstaller build.spec
```

### With pip

```
# Create a new virtual env
python -m venv ./venv

# Activate the venv (Windows)
./venv/Scripts/activate.bat

# Activate the venv (Unix/linux)
source ./venv/Scripts/activate

pip install -r requirements.txt

python -m PyInstaller build.spec
```
