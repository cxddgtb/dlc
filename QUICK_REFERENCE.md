# CXDDZY-Pro v2.0 快速参考

## 🚀 一分钟上手

```bash
# 1. 克隆项目
git clone https://github.com/cxddgtb/cxddzy-pro.git
cd cxddzy-pro

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python main.py

# 4. 查看结果
ls output/
```

---

## 📁 项目结构速览

```
cxddzy-pro/
├── src/                # 源代码
│   ├── core/          # 核心模块
│   ├── protocols/     # 协议解析
│   ├── output/        # 输出生成
│   └── utils/         # 工具函数
├── config/            # 配置文件
│   ├── sources.list   # 订阅源
│   └── clash.yml      # Clash模板
├── output/            # 输出目录（自动生成）
├── main.py            # 主入口
└── requirements.txt   # 依赖列表
```

---

## 🔧 常用命令

### 基本操作

```bash
# 运行程序
python main.py

# 调试模式
LOG_LEVEL=DEBUG python main.py

# 自定义并发数
MAX_CONCURRENT=30 python main.py
```

### Windows快捷方式

```bash
# 双击运行
run.bat
```

### Linux/Mac快捷方式

```bash
chmod +x run.sh
./run.sh
```

---

## 📊 输出文件说明

| 文件名 | 格式 | 用途 |
|--------|------|------|
| list.txt | Base64 | V2Ray订阅 |
| list.yml | YAML | Clash配置 |
| list.meta.yml | YAML | Clash Meta配置 |
| list_raw.txt | 纯文本 | 原始URL |

---

## ⚙️ 环境变量

```bash
LOG_LEVEL=INFO|DEBUG|WARNING|ERROR
MAX_CONCURRENT=20
REQUEST_TIMEOUT=30
MAX_RETRIES=3
ENABLE_VALIDATION=false
```

---

## 🔍 故障排查

### 问题：没有抓取到节点

```bash
# 检查网络
ping github.com

# 查看详细日志
LOG_LEVEL=DEBUG python main.py

# 更新源列表
# 编辑 config/sources.list
```

### 问题：速度太慢

```bash
# 增加并发
MAX_CONCURRENT=30 python main.py

# 减少超时
REQUEST_TIMEOUT=15 python main.py
```

### 问题：内存占用高

```bash
# 减少并发
MAX_CONCURRENT=10 python main.py
```

---

## 📝 配置示例

### sources.list

```
https://raw.githubusercontent.com/user/repo/main/nodes.txt
https://example.com/subscribe/v2ray
```

### 添加新源

1. 打开 `config/sources.list`
2. 每行添加一个URL
3. 保存并重新运行

---

## 🎯 性能优化建议

| 场景 | 推荐配置 |
|------|----------|
| 快速测试 | MAX_CONCURRENT=5, TIMEOUT=10 |
| 日常使用 | MAX_CONCURRENT=20, TIMEOUT=30 |
| 大规模抓取 | MAX_CONCURRENT=50, TIMEOUT=60 |
| 低配机器 | MAX_CONCURRENT=5, TIMEOUT=30 |

---

## 📖 更多信息

- **完整文档**: README.md
- **技术细节**: PROJECT_SUMMARY.md
- **使用指南**: USAGE_GUIDE.md
- **GitHub**: https://github.com/cxddgtb/cxddzy-pro

---

**版本**: v2.0.0
**更新**: 2026-04-25
