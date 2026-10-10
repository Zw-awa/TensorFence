# 零基础安装指南

[English](./setup-beginner.md)

这份文档是写给完全小白的：

- 不懂 Python
- 不懂 Conda
- 不懂 WSL
- 不懂“环境管理”是什么

如果你只记住一句话：

- Windows 上用 `Miniforge3` 做 TensorFence 开发环境
- WSL2 + Ubuntu 22.04 + `Miniforge3` 做 RKNN 环境

为什么默认推荐 Miniforge3：

- TensorFence 主要用的是 `conda-forge` 风格的包
- Miniforge3 更轻、更简单
- 这个项目不需要完整的 Anaconda 大礼包

如果你的学校、公司或者团队已经明确要求使用 Anaconda，你当然也可以继续用。
但如果你选 Anaconda，请你自己先确认所在组织对它的条款、使用范围和合规要求。

常用链接：

- Miniforge 官方仓库：<https://github.com/conda-forge/miniforge>
- WSL 官方安装文档：<https://learn.microsoft.com/windows/wsl/install>
- 清华 Conda 镜像帮助：<https://mirror.tuna.tsinghua.edu.cn/help/anaconda/>
- RKNN-Toolkit2 官方仓库：<https://github.com/airockchip/rknn-toolkit2>

## 1. 你到底要装什么

你最终会有两套环境：

1. Windows 开发环境
   用来跑 TensorFence 的日常开发和命令，比如：
   - `doctor`
   - `check-contract`
   - `inspect-image`
   - `probe-model`
   - `draft-contract`
   - `compare-stages`

2. WSL/Linux RKNN 环境
   用来装 RKNN-Toolkit2，做 RKNN 转换、连板、精度分析这类工作。

不要试图把所有东西都硬塞进一个 Windows Python 环境里。

## 2. 在 Windows 上安装 Conda

### 方案 A：Miniforge3（推荐）

1. 打开 Miniforge 官方发布页
2. 下载适合你电脑的 Windows 安装包
   大多数用户选 64 位 Windows 安装包即可
3. 双击运行安装程序
4. 没有特殊需求就一路默认
5. 安装完成

安装完成后，打开下面任意一种终端：

- `Miniforge Prompt`
- `Windows Terminal`
- `PowerShell`

然后输入：

```powershell
conda --version
```

如果能看到版本号，说明 Conda 已经装好了。

### 方案 B：Anaconda

只有在下面情况才建议选 Anaconda：

- 你已经知道自己为什么要用它
- 或者你的学校/公司/团队已经统一要求它

对 TensorFence 来说，Anaconda 不是必须的。

## 3. 可选：在 Windows 上配置清华镜像

如果你在中国大陆，很多时候下载包会更快。

先打开 PowerShell 或 Conda 终端，执行：

```powershell
conda config --set show_channel_urls yes
```

这一步的作用是先生成 Conda 配置文件。

然后找到这个文件：

- Windows 路径：`C:\Users\<你的用户名>\.condarc`

把内容改成：

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

然后刷新 Conda 索引缓存：

```powershell
conda clean -i
```

如果你已经有自己能正常使用的 Conda 镜像配置，可以继续用自己的，不必强改。

## 4. 创建 Windows 版 TensorFence 环境

Windows 和 WSL 的 Conda 是两个独立安装。可以只安装其中一个：只做本机诊断时只需要 Windows Conda；做 RKNN 时才需要 WSL Conda。项目不会假设两边同时存在，也不会自动跨环境安装依赖。

在 TensorFence 仓库根目录打开 PowerShell，然后运行：

```powershell
conda env create -f environment.yml
conda activate tensorfence
```

然后把当前项目安装进这个环境：

```powershell
pip install -e .
```

如果你的机器上 `pip install -e .` 因为临时目录权限失败，也不要慌。
你仍然可以先用源码模式运行：

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m tensorfence doctor
```

## 5. 验证 Windows 环境

执行：

```powershell
conda activate tensorfence
tensorfence doctor
```

正常情况下，你会看到类似：

- `numpy: ok`
- `pydantic: ok`
- `onnx: ok`

如果你没成功做 `pip install -e .`，那就用：

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m tensorfence doctor
```

## 6. 安装 WSL2

WSL 可以理解成“Windows 里的 Linux”。

用管理员身份打开 PowerShell，然后运行：

```powershell
wsl --install
```

如果系统提示重启，就重启电脑。

重启后，Windows 通常会继续安装 Ubuntu。

你可以用下面命令查看 WSL 是否已经装好：

```powershell
wsl -l -v
```

## 7. 选择 Linux 发行版

对于 TensorFence 的 RKNN 流程，建议直接用：

- `Ubuntu 22.04`

原因：

- Rockchip 自己的 WSL 说明里明确说 Ubuntu 22.04 是验证过的版本

如果你的电脑里还没有 Ubuntu，可以：

- 用 Microsoft Store 安装
- 或者按 WSL 官方文档继续安装

## 8. 第一次打开 Ubuntu

从开始菜单里打开 `Ubuntu`。

第一次启动通常会稍微慢一点。
它会让你创建：

- 一个 Linux 用户名
- 一个 Linux 密码

注意：

- 这个账号和你的 Windows 账号不是同一个东西

## 9. 在 WSL 里安装 Miniforge3

先在 Ubuntu 终端里安装几个基础工具：

```bash
sudo apt update
sudo apt install wget bzip2 -y
```

然后去 Miniforge 官方发布页下载 Linux 安装脚本。

如果你已经拿到了下载链接，通常安装流程长这样：

```bash
wget <Miniforge-Linux-installer-url> -O Miniforge3.sh
bash Miniforge3.sh
```

安装过程中：

- 按 `Enter` 继续
- 看到协议后输入 `yes`
- 安装路径没有特殊需求就用默认值

装完后，重新打开终端，或者执行安装器提示你的初始化命令。

然后检查：

```bash
conda --version
```

## 10. 可选：在 WSL 里配置清华镜像

在 Ubuntu 终端里，编辑你的 Conda 配置文件：

```bash
nano ~/.condarc
```

把内容改成：

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

保存后执行：

```bash
conda clean -i
```

## 11. 创建 WSL 版 TensorFence 环境

在 WSL 里进入 TensorFence 仓库。

如果仓库在 Windows 的某个盘符里，那么在 WSL 里通常会映射成 `/mnt/<盘符小写>/...`。

示例形式：

```bash
export TENSORFENCE_ROOT=/mnt/<盘符小写>/<TensorFence 的路径>
cd "$TENSORFENCE_ROOT"
```

然后创建 WSL 环境：

```bash
conda env create -f environment.wsl.yml
conda activate tensorfence-wsl
```

安装 TensorFence：

```bash
pip install -e .
```

再验证：

```bash
tensorfence doctor
```

## 12. 在 WSL 里安装 RKNN-Toolkit2

这一步要在 `tensorfence-wsl` 环境中做。

非常重要：

- 只从 Rockchip 官方仓库获取 RKNN-Toolkit2
- 下载和你 Python 版本、Linux 架构匹配的 wheel

对于 `Linux x86_64 + Python 3.12`，wheel 文件名通常长这样：

```text
rknn_toolkit2-<版本>-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

安装命令类似：

```bash
pip install /path/to/rknn_toolkit2-...cp312...x86_64.whl
```

如果安装成功，可以验证：

```bash
python -c "import rknn"
```

## 13. 最常用的第一批命令

Windows 开发环境：

```powershell
conda activate tensorfence
tensorfence doctor
tensorfence check-contract examples\detection_contract.yaml
```

WSL 的 RKNN 环境：

```bash
conda activate tensorfence-wsl
tensorfence doctor
```

## 14. 如果报错怎么办

如果提示找不到 `conda`：

- 先关掉终端
- 重新打开
- 再执行 `conda --version`

如果安装完以后提示找不到 `tensorfence`：

- 先确认环境是否已经激活
- 然后试试：

```bash
python -m tensorfence doctor
```

如果 WSL 里 `rknn` 导入失败：

- 先检查你装的是不是 Linux wheel
- 再检查 wheel 是否和 Python 版本一致
- 再去看 Rockchip 官方文档是否还要求额外系统库

## 15. 推荐的最终结构

- Windows
  - `tensorfence` 环境，负责开发和调试 TensorFence
- WSL
  - `tensorfence-wsl` 环境，负责 RKNN 工具链和真机相关流程

这样分开最干净，也最容易排错。
