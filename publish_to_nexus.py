#!/usr/bin/env python3
"""
推送 Python 包到 Nexus 私服脚本
凭证从本地 .nexus_credentials 文件或环境变量读取
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def load_credentials():
    """从 .nexus_credentials 文件或环境变量加载凭证"""
    credentials_file = Path(__file__).parent / ".nexus_credentials"
    
    # 加载凭证文件（不覆盖已有的环境变量）
    if credentials_file.exists():
        print(f"已加载凭证文件：{credentials_file}")
        with open(credentials_file) as f:
            for line in f:
                line = line.strip()
                # 跳过注释和空行
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    # 环境变量优先，文件中的作为默认值
                    if key not in os.environ:
                        os.environ[key] = value

    # 读取凭证
    url = os.environ.get("NEXUS_URL")
    username = os.environ.get("NEXUS_USERNAME")
    password = os.environ.get("NEXUS_PASSWORD")

    # 检查必要凭证
    if not all([url, username, password]):
        print("错误：缺少 Nexus 凭证配置", file=sys.stderr)
        print("请创建 .nexus_credentials 文件（参考 .nexus_credentials.example）", file=sys.stderr)
        print("或设置以下环境变量：", file=sys.stderr)
        print("  export NEXUS_URL=...", file=sys.stderr)
        print("  export NEXUS_USERNAME=...", file=sys.stderr)
        print("  export NEXUS_PASSWORD=...", file=sys.stderr)
        sys.exit(1)

    return url, username, password


def run_command(cmd, check=True):
    """运行命令并打印输出"""
    print(f"执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=check, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result


def clean_build():
    """清理旧的构建产物"""
    print("清理旧的构建产物...")
    for dir_name in ["dist", "build"]:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"  已删除: {dir_name}/")
    for egg_info in Path(".").glob("*.egg-info"):
        shutil.rmtree(egg_info)
        print(f"  已删除: {egg_info}")


def build_package():
    """构建 Python 包"""
    print("安装构建依赖...")
    run_command([sys.executable, "-m", "pip", "install", "--upgrade", "build", "twine"])

    print("构建 Python 包...")
    run_command([sys.executable, "-m", "build"])

    dist_dir = Path("dist")
    if not dist_dir.exists() or not list(dist_dir.iterdir()):
        print("错误：构建失败，dist 目录为空", file=sys.stderr)
        sys.exit(1)

    print("\n构建完成，生成的文件：")
    for file in dist_dir.iterdir():
        size = file.stat().st_size / 1024
        print(f"  {file.name} ({size:.1f} KB)")


def upload_to_nexus(url, username, password):
    """推送到 Nexus 私服"""
    print(f"\n推送到 Nexus 私服：{url}")
    run_command([
        sys.executable, "-m", "twine", "upload",
        "--repository-url", url,
        "--username", username,
        "--password", password,
        "--verbose",
        "dist/*",
    ])


def main():
    print("=" * 50)
    print("开始构建和推送到 Nexus 私服")
    print("=" * 50)
    print()

    try:
        url, username, password = load_credentials()
        print(f"目标地址：{url}\n")

        clean_build()
        print()

        build_package()
        print()

        upload_to_nexus(url, username, password)
        print()

        print("=" * 50)
        print("推送完成！")
        print("=" * 50)

    except subprocess.CalledProcessError as e:
        print(f"\n错误：命令执行失败，返回码: {e.returncode}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n错误：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
