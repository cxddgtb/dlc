# CXDDZY-Pro v2.0 使用指南

## 📖 目录

1. [快速开始](#快速开始)
2. [安装依赖](#安装依赖)
3. [配置说明](#配置说明)
4. [运行程序](#运行程序)
5. [输出文件](#输出文件)
6. [常见问题](#常见问题)
7. [高级用法](#高级用法)

---

## 快速开始

### Windows用户

双击运行 `run.bat` 即可自动完成安装和运行。

### Linux/Mac用户

```bash
chmod +x run.sh
./run.sh
```

---

## 安装依赖

### 方法一：使用pip（推荐）

```bash
pip install -r requirements.txt
```

### 方法二：使用pyproject.toml

```bash
pip install .
```

### 所需依赖

- `aiohttp>=3.9.0` - 异步HTTP客户端
- `pyyaml>=6.0` - YAML配置文件解析
- `pydantic>=2.5.0` - 数据验证
- `loguru>=0.7.0` - 日志系统
- `aiosqlite>=0.19.0` - 异步SQLite支持

---

## 配置说明

### 1. 订阅源配置 (config/sources.list)

每行一个URL，支持以下格式：

```
# GitHub Raw链接
https://raw.githubusercontent.com/user/repo/main/nodes.txt

# 直连订阅
https://example.com/subscribe/v2ray

# 本地文件（开发用）
file:///path/to/local/nodes.txt
```

**建议**：
- 添加5-20个稳定源
- 定期更新失效源
- 避免重复源浪费资源

### 2. Clash配置 (config/clash.yml)

主要配置项：

```yaml
# 端口设置
port: 7890              # HTTP代理端口
socks-port: 7891        # SOCKS代理端口
mixed-port: 7892        # 混合端口

# DNS配置
dns:
  enable: true
  nameserver:
    - 223.5.5.5         # 阿里DNS
    - 114.114.114.114   # 114DNS
  fallback:
    - 8.8.8.8           # Google DNS
    - 1.1.1.1           # Cloudflare DNS

# 策略组
proxy-groups:
  - name: "🚀 节点选择"
    type: select
    proxies: [...]
```

### 3. 环境变量 (.env)

复制 `.env.example` 为 `.env` 并修改：

```bash
LOG_LEVEL=INFO              # 日志级别
MAX_CONCURRENT=20           # 最大并发数
REQUEST_TIMEOUT=30          # 请求超时(秒)
ENABLE_VALIDATION=false     # 启用验证
```

---

## 运行程序

### 基本运行

```bash
python main.py
```

### 详细模式

```bash
LOG_LEVEL=DEBUG python main.py
```

### 自定义配置

```bash
SOURCES_FILE=my_sources.list python main.py
```

### 后台运行（Linux）

```bash
nohup python main.py > fetch.log 2>&1 &
```

---

## 输出文件

运行完成后，在 `output/` 目录下生成：

### 1. list.txt (V2Ray订阅)

**格式**: Base64编码
**用途**: V2RayN, V2RayNG, Shadowrocket等客户端
**大小**: 通常1-5MB

**使用方法**:
```
在客户端中选择"从URL导入订阅"
输入: https://cdn.jsdelivr.net/gh/your/repo@master/output/list.txt
```

### 2. list.yml (Clash配置)

**格式**: YAML
**用途**: Clash, Clash for Windows, ClashiX
**特点**: 包含完整策略组和规则

**使用方法**:
```
复制到Clash配置目录
或在客户端中导入URL
```

### 3. list.meta.yml (Clash Meta配置)

**格式**: YAML (增强版)
**用途**: Clash Meta, Mihomo
**特性**:
- 支持Sniffer嗅探
- 更多协议支持
- 高级路由功能

### 4. list_raw.txt (原始URL)

**格式**: 纯文本，每行一个URL
**用途**: 调试、二次处理
**示例**:
```
vmess://eyJ2IjoiMiIsInBzIjoi...
ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@...
trojan://password@server:443#name
```

---

## 常见问题

### Q1: 提示"No nodes fetched"

**原因**:
- 所有源都失效
- 网络连接问题
- 源内容为空

**解决方法**:
1. 检查网络连接
2. 更新sources.list中的源
3. 使用DEBUG模式查看详细错误

```bash
LOG_LEVEL=DEBUG python main.py
```

### Q2: 抓取速度很慢

**优化方法**:

1. 增加并发数
```bash
MAX_CONCURRENT=30 python main.py
```

2. 减少超时时间
```bash
REQUEST_TIMEOUT=15 python main.py
```

3. 减少源数量（保留高质量源）

### Q3: 内存占用过高

**解决方法**:

1. 限制并发数
```bash
MAX_CONCURRENT=10 python main.py
```

2. 分批处理源
```python
# 修改main.py，将源分组处理
```

### Q4: 节点质量差

**优化方法**:

1. 启用节点验证
```bash
ENABLE_VALIDATION=true python main.py
```

2. 调整去重策略
```python
# 在main.py中修改
deduplicator = Deduplicator(strategy="best")
```

3. 增加评分权重
```python
# 修改node.py中的calculate_score方法
```

### Q5: GitHub Actions失败

**常见原因**:
- 超时（超过30分钟）
- Git冲突
- 网络问题

**解决方法**:
1. 检查工作流日志
2. 手动触发重试
3. 减少源数量或超时时间

---

## 高级用法

### 1. 自定义地区分类

创建 `config/regions.yml`:

```yaml
CUSTOM_REGION:
  keywords: ["关键词1", "关键词2"]
  name: "自定义地区"

ANOTHER_REGION:
  keywords: ["key1", "key2"]
  name: "另一个地区"
```

### 2. 添加新协议支持

在 `src/protocols/` 创建解析器：

```python
# src/protocols/new_protocol.py
from typing import Optional
from src.core.node import Node, Protocol

def parse_new_protocol(url: str, source_url: str = None) -> Optional[Node]:
    # 实现解析逻辑
    pass
```

注册到 `src/protocols/__init__.py`

### 3. 自定义输出生成器

继承 `BaseOutputGenerator`:

```python
from src.output.base import BaseOutputGenerator

class CustomGenerator(BaseOutputGenerator):
    def generate(self, nodes):
        # 实现自定义输出格式
        pass
```

### 4. 集成到现有系统

作为Python模块使用：

```python
import asyncio
from src.core.fetcher import Fetcher
from src.core.deduplicator import Deduplicator

async def custom_fetch():
    sources = ["https://example.com/nodes.txt"]

    async with Fetcher() as fetcher:
        nodes = await fetcher.fetch_all_sources(sources)

    dedup = Deduplicator()
    unique_nodes = dedup.deduplicate(nodes)

    return unique_nodes

# 运行
nodes = asyncio.run(custom_fetch())
```

### 5. 定时任务（Linux Cron）

```cron
# 每3小时执行一次
0 */3 * * * cd /path/to/cxddzy-pro && python main.py >> /var/log/cxddzy.log 2>&1
```

### 6. Docker部署（未来支持）

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt

CMD ["python", "main.py"]
```

---

## 性能调优

### 最佳实践配置

```bash
# 生产环境推荐
MAX_CONCURRENT=20
REQUEST_TIMEOUT=30
MAX_RETRIES=3
LOG_LEVEL=WARNING
ENABLE_VALIDATION=false

# 开发调试
MAX_CONCURRENT=5
REQUEST_TIMEOUT=10
MAX_RETRIES=1
LOG_LEVEL=DEBUG
ENABLE_VALIDATION=true
```

### 硬件要求

| 规模 | CPU | 内存 | 网络 |
|------|-----|------|------|
| 小型 (<50节点) | 1核 | 256MB | 1Mbps |
| 中型 (50-200节点) | 2核 | 512MB | 5Mbps |
| 大型 (>200节点) | 4核 | 1GB | 10Mbps |

---

## 故障排除

### 查看日志

```bash
# 实时查看
tail -f logs/fetch_2026-04-25.log

# 搜索错误
grep "ERROR" logs/fetch_*.log
```

### 清理缓存

```bash
# 删除输出文件
rm -rf output/*

# 删除日志
rm -rf logs/*

# 重新运行
python main.py
```

### 重置配置

```bash
# 备份自定义配置
cp config/sources.list sources.list.bak

# 恢复默认
git checkout config/

# 恢复自定义
cp sources.list.bak config/sources.list
```

---

## 获取帮助

### 文档

- README.md - 项目介绍
- PROJECT_SUMMARY.md - 技术总结
- USAGE_GUIDE.md - 本文件

### 社区

- GitHub Issues - 报告问题
- Discussions - 讨论交流

### 联系方式

- Email: support@cxddzy.pro (示例)
- Telegram: @cxddzy_pro (示例)

---

**最后更新**: 2026-04-25
**版本**: v2.0.0

*Happy Fetching! 🚀*
