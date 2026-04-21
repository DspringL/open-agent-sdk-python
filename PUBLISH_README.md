# 推送到 Nexus 私服说明

## 使用方法

### 方式一：使用 Bash 脚本（推荐 Linux/macOS）

```bash
./publish_to_nexus.sh
```

### 方式二：使用 Python 脚本（跨平台）

```bash
python publish_to_nexus.py
```

或者：

```bash
python3 publish_to_nexus.py
```

## 脚本功能

两个脚本功能相同，都会执行以下操作：

1. **清理旧的构建产物** - 删除 `dist/`、`build/` 和 `*.egg-info/` 目录
2. **安装构建依赖** - 自动安装 `build` 和 `twine` 工具
3. **构建 Python 包** - 生成 wheel 和 tar.gz 分发包
4. **推送到 Nexus** - 上传到私服仓库

## 前置要求

- Python 3.10 或更高版本
- 网络可访问 `https://nexus.hanokl.com`

## 注意事项

⚠️ **安全提示**：
- 这两个脚本包含敏感的私服凭证信息
- 已在 `.gitignore` 中排除，**不会被提交到 GitHub**
- 请妥善保管，不要分享给未授权人员

## 手动推送（可选）

如果需要手动控制推送过程：

```bash
# 1. 清理旧构建
rm -rf dist/ build/ *.egg-info/

# 2. 安装依赖
pip install --upgrade build twine

# 3. 构建包
python -m build

# 4. 推送到 Nexus
python -m twine upload \
    --repository-url https://nexus.hanokl.com/repository/hk-python-hosted \
    --username develop \
    --password rWs0VNaF2dZV35hR \
    dist/*
```

## 从私服安装

推送成功后，可以从私服安装包：

```bash
pip install open-agent-sdk \
    --index-url https://develop:rWs0VNaF2dZV35hR@nexus.hanokl.com/repository/hk-python-hosted/simple
```

或配置 `pip.conf` / `pip.ini`：

```ini
[global]
index-url = https://develop:rWs0VNaF2dZV35hR@nexus.hanokl.com/repository/hk-python-hosted/simple
```

## 故障排查

### 构建失败
- 检查 Python 版本是否 >= 3.10
- 确保 `pyproject.toml` 配置正确

### 上传失败
- 检查网络连接
- 验证私服地址和凭证是否正确
- 确认版本号是否已存在（Nexus 可能不允许覆盖）

### 权限错误
- 确保脚本有执行权限：`chmod +x publish_to_nexus.sh`
- 检查当前用户是否有写入 `dist/` 目录的权限
