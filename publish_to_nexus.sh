#!/bin/bash
# 推送 Python 包到 Nexus 私服脚本
# 凭证从本地 .nexus_credentials 文件或环境变量读取

set -e

# 加载本地凭证文件（优先级低于环境变量）
CREDENTIALS_FILE="$(dirname "$0")/.nexus_credentials"
if [ -f "$CREDENTIALS_FILE" ]; then
    # shellcheck source=.nexus_credentials
    source "$CREDENTIALS_FILE"
    echo "已加载凭证文件：$CREDENTIALS_FILE"
fi

# 检查必要的凭证变量
if [ -z "$NEXUS_URL" ] || [ -z "$NEXUS_USERNAME" ] || [ -z "$NEXUS_PASSWORD" ]; then
    echo "错误：缺少 Nexus 凭证配置"
    echo "请创建 .nexus_credentials 文件（参考 .nexus_credentials.example）"
    echo "或设置以下环境变量："
    echo "  export NEXUS_URL=..."
    echo "  export NEXUS_USERNAME=..."
    echo "  export NEXUS_PASSWORD=..."
    exit 1
fi

echo "=========================================="
echo "开始构建和推送到 Nexus 私服"
echo "目标地址：$NEXUS_URL"
echo "=========================================="

# 清理旧的构建产物
echo "清理旧的构建产物..."
rm -rf dist/ build/ *.egg-info/

# 安装构建依赖
echo "安装构建依赖..."
python -m pip install --upgrade build twine

# 构建包
echo "构建 Python 包..."
python -m build

# 检查构建产物
if [ ! -d "dist" ] || [ -z "$(ls -A dist)" ]; then
    echo "错误：构建失败，dist 目录为空"
    exit 1
fi

echo "构建完成，生成的文件："
ls -lh dist/

# 推送到 Nexus
echo "推送到 Nexus 私服..."
python -m twine upload \
    --repository-url "$NEXUS_URL" \
    --username "$NEXUS_USERNAME" \
    --password "$NEXUS_PASSWORD" \
    --verbose \
    dist/*

echo "=========================================="
echo "推送完成！"
echo "=========================================="
