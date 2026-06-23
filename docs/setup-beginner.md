# Beginner Setup Guide

[中文版本](./setup-beginner.zh-CN.md)

This guide is for people who are completely new to Python, Conda, WSL, and environment setup.

If you only want one recommendation:

- Use `Miniforge3` on Windows for TensorFence development.
- Use `WSL2 + Ubuntu 22.04 + Miniforge3` for RKNN work.

Why this guide recommends Miniforge3 first:

- TensorFence uses `conda-forge`-friendly packages.
- Miniforge3 is smaller and simpler than full Anaconda.
- You do not need the full Anaconda distribution for this project.

If your school or company already standardizes on Anaconda, you can still use it.
If you choose Anaconda, verify its terms and internal compliance requirements yourself before using it in your organization.

Useful links:

- Miniforge official repository: <https://github.com/conda-forge/miniforge>
- WSL official installation guide: <https://learn.microsoft.com/windows/wsl/install>
- Tsinghua Conda mirror help: <https://mirror.tuna.tsinghua.edu.cn/help/anaconda/>
- RKNN-Toolkit2 official repository: <https://github.com/airockchip/rknn-toolkit2>

## 1. What You Are Installing

You will prepare two environments:

1. Windows development environment
   Use this for TensorFence CLI, contract checking, image inspection, ONNX probing, draft generation, and most day-to-day development.

2. WSL/Linux RKNN environment
   Use this for RKNN-Toolkit2, model conversion, and board-side workflows.

Do not try to merge everything into one Windows Python environment.

## 2. Install Conda on Windows

### Option A: Miniforge3 (Recommended)

1. Open the Miniforge release page.
2. Download the Windows installer for your machine.
   Most users should choose the 64-bit Windows installer.
3. Run the installer.
4. Keep the default install location unless you have a specific reason not to.
5. Finish the installation.

After installation, open:

- `Miniforge Prompt`, or
- `Windows Terminal`, or
- `PowerShell`

Then check that Conda works:

```powershell
conda --version
```

### Option B: Anaconda

Choose Anaconda only if:

- you already know you need it, or
- your organization already approved it.

TensorFence does not require Anaconda specifically.

## 3. Optional: Configure the Tsinghua Mirror on Windows

If you are in mainland China, package downloads may be faster with the Tsinghua mirror.

Open PowerShell or your Conda prompt and run:

```powershell
conda config --set show_channel_urls yes
```

Then open your Conda configuration file:

- Windows path: `C:\Users\<YourUserName>\.condarc`

Replace its content with:

```yaml
channels:
  - defaults
show_channel_urls: true
default_channels:
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/msys2
custom_channels:
  conda-forge: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
  pytorch: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
```

Then refresh Conda's cache:

```powershell
conda clean -i
```

If you already have your own Conda mirror configuration and it works, keep using it.

## 4. Create the Windows TensorFence Environment

Open PowerShell in the TensorFence repository root and run:

```powershell
conda env create -f environment.yml
conda activate tensorfence
```

Then install TensorFence itself in editable mode:

```powershell
pip install -e .
```

If `pip install -e .` fails because of temporary directory permissions on your machine, you can still run TensorFence like this:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m tensorfence doctor
```

## 5. Verify the Windows Environment

Run:

```powershell
conda activate tensorfence
tensorfence doctor
```

You should see package checks such as:

- `numpy: ok`
- `pydantic: ok`
- `onnx: ok`

If you installed from source mode instead of `pip install -e .`, use:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m tensorfence doctor
```

## 6. Install WSL2

WSL is Microsoft's Linux environment on Windows.

Open PowerShell as Administrator and run:

```powershell
wsl --install
```

Then restart Windows if prompted.

After restart, Windows usually installs Ubuntu automatically.

To check your installed Linux distributions:

```powershell
wsl -l -v
```

## 7. Choose a Linux Distribution

For TensorFence RKNN work, use:

- `Ubuntu 22.04`

Why:

- Rockchip's own WSL note explicitly says Ubuntu 22.04 has been verified.

If Ubuntu is not installed yet, you can install it from the Microsoft Store or with WSL commands.

## 8. Open Ubuntu in WSL

Launch `Ubuntu` from the Start menu.

The first launch may take a few minutes.
It will ask you to create:

- a Linux username
- a Linux password

This Linux account is separate from your Windows account.

## 9. Install Miniforge3 Inside WSL

Inside the Ubuntu terminal, install a few basic tools first:

```bash
sudo apt update
sudo apt install wget bzip2 -y
```

Then download a Miniforge installer for Linux from the official Miniforge releases page.

If you already know the exact file name, it usually looks like this pattern:

```bash
wget <Miniforge-Linux-installer-url> -O Miniforge3.sh
bash Miniforge3.sh
```

During installation:

- press `Enter` to continue
- type `yes` when asked to accept
- accept the default install path unless you know you want another location

After installation, restart the terminal or run the shell initialization command suggested by the installer.

Then check:

```bash
conda --version
```

## 10. Optional: Configure the Tsinghua Mirror in WSL

Inside Ubuntu, create or edit `~/.condarc`:

```bash
nano ~/.condarc
```

Paste:

```yaml
channels:
  - defaults
show_channel_urls: true
default_channels:
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/msys2
custom_channels:
  conda-forge: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
  pytorch: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
```

Then run:

```bash
conda clean -i
```

## 11. Create the WSL TensorFence Environment

Inside WSL, go to the TensorFence repository.

If the repository is on a Windows drive, it is usually visible in WSL under `/mnt/<drive-letter-lowercase>/...`.

Example pattern:

```bash
export TENSORFENCE_ROOT=/mnt/<drive-letter-lowercase>/<path-to-TensorFence>
cd "$TENSORFENCE_ROOT"
```

Create the WSL environment:

```bash
conda env create -f environment.wsl.yml
conda activate tensorfence-wsl
```

Install TensorFence:

```bash
pip install -e .
```

Verify:

```bash
tensorfence doctor
```

## 12. Install RKNN-Toolkit2 in WSL

Do this inside the `tensorfence-wsl` environment.

Important:

- Use the official Rockchip repository as the source.
- Download the wheel that matches:
  - your Python version
  - your Linux architecture

For Python 3.12 on Linux x86_64, the file name pattern looks like:

```text
rknn_toolkit2-<version>-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

Then install it:

```bash
pip install /path/to/rknn_toolkit2-...cp312...x86_64.whl
```

If installation succeeds, verify:

```bash
python -c "import rknn"
```

## 13. Common First Commands

Windows development environment:

```powershell
conda activate tensorfence
tensorfence doctor
tensorfence check-contract examples\detection_contract.yaml
```

WSL RKNN environment:

```bash
conda activate tensorfence-wsl
tensorfence doctor
```

## 14. If Something Fails

If `conda` is not found:

- close the terminal
- reopen it
- run `conda --version` again

If `tensorfence` is not found after installation:

- make sure the environment is activated
- try:

```bash
python -m tensorfence doctor
```

If RKNN import fails in WSL:

- check that you installed the Linux wheel, not a Windows file
- check that the wheel matches your Python version
- check Rockchip's official RKNN documents for extra system libraries

## 15. Recommended Final Layout

- Windows
  - `tensorfence` environment for development
- WSL
  - `tensorfence-wsl` environment for RKNN work

This separation is simpler, cleaner, and easier to debug.
