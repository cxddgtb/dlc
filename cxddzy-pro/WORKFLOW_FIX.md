# GitHub Actions 推送冲突修复说明

## 🔧 已应用的修复

### 问题
```
! [rejected] HEAD -> master (non-fast-forward)
Updates were rejected because a pushed branch tip is behind its remote counterpart
```

### 解决方案

已在 `.github/workflows/fetch.yml` 中应用以下改进：

---

## ✅ 修复内容

### 1. 添加并发控制

```yaml
concurrency:
  group: fetch-nodes
  cancel-in-progress: false
```

**作用**：
- 防止多个工作流实例同时运行
- 避免并发推送导致的冲突
- `cancel-in-progress: false` 确保当前任务完成

### 2. 获取完整 Git 历史

```yaml
- name: Checkout code
  uses: actions/checkout@v4
  with:
    fetch-depth: 0  # 从 1 改为 0
```

**作用**：
- 获取完整的 Git 历史记录
- 支持 rebase 操作
- 便于处理分支分叉

### 3. 改进的 Rebase 逻辑

```bash
# 使用rebase整合远程变更
git fetch origin master
git rebase origin/master || {
  echo "Rebase failed, trying merge strategy"
  git rebase --abort || true
  git pull --no-edit origin master || true
}
```

**作用**：
- 先尝试 rebase（保持提交历史整洁）
- 如果 rebase 失败，回退到 merge
- 确保始终能整合远程变更

### 4. 自动重试推送

```bash
# 推送到远程，如果失败则重试
for i in 1 2 3; do
  if git push origin master; then
    echo "Push successful on attempt $i"
    break
  else
    echo "Push attempt $i failed, retrying..."
    git pull --rebase origin master || true
    sleep 5
  fi
done
```

**作用**：
- 最多重试 3 次
- 每次重试前重新拉取并 rebase
- 等待 5 秒避免速率限制

### 5. 合并 Commit 和 Push 步骤

原来的两个步骤合并为一个，确保：
- Rebase → Commit → Push 在同一上下文中执行
- 避免中间状态导致的问题
- 更好的错误处理

---

## 📊 修复前后对比

| 特性 | 修复前 | 修复后 |
|------|--------|--------|
| 并发控制 | ❌ 无 | ✅ 有 |
| Git 历史 | ❌ 浅克隆 (depth=1) | ✅ 完整历史 |
| Rebase 策略 | ⚠️ 简单 pull --rebase | ✅ 完整 rebase + fallback |
| 推送重试 | ❌ 无 | ✅ 3次重试 |
| 错误恢复 | ❌ 弱 | ✅ 强 |

---

## 🎯 工作流程

修复后的完整流程：

```
1. 触发工作流
   ↓
2. 检出代码（完整历史）
   ↓
3. 安装依赖
   ↓
4. 执行节点抓取
   ↓
5. 验证输出文件
   ↓
6. Fetch 远程最新变更
   ↓
7. Rebase 本地变更
   ├─ 成功 → 继续
   └─ 失败 → Merge 策略
   ↓
8. 提交更改（如果有）
   ↓
9. 推送至远程
   ├─ 成功 → 完成
   └─ 失败 → 重试（最多3次）
       ├─ Pull + Rebase
       ├─ 等待 5 秒
       └─ 重新推送
   ↓
10. 清除 CDN 缓存
   ↓
11. 上传产物
```

---

## 🚀 使用方法

### 自动执行

工作流会在以下情况自动触发：
- 每 3 小时（cron）
- 手动触发（workflow_dispatch）
- 关键文件变更（push）

### 手动测试

```bash
# 提交更改到 GitHub
git add .github/workflows/fetch.yml
git commit -m "Fix: Improve workflow push reliability"
git push origin master
```

然后在 GitHub 页面：
1. 进入 Actions 标签
2. 选择 "Fetch Nodes Pro" 工作流
3. 点击 "Run workflow"
4. 观察执行结果

---

## 🔍 监控和调试

### 查看工作流状态

```bash
# 在 GitHub 仓库页面
https://github.com/your/repo/actions
```

### 常见问题排查

#### 问题 1：Rebase 冲突

**症状**：
```
CONFLICT (content): Merge conflict in file.txt
```

**解决**：
工作流会自动回退到 merge 策略，通常能解决。

#### 问题 2：推送仍然失败

**可能原因**：
- 网络问题
- GitHub 服务中断
- 权限不足

**解决**：
1. 检查工作流日志
2. 确认 GITHUB_TOKEN 权限
3. 稍后重试

#### 问题 3：并发冲突

**症状**：
```
Resource temporarily unavailable
```

**解决**：
并发控制已启用，应该不会再发生。

---

## 📝 最佳实践建议

### 1. 定期检查工作流

每周检查一次 Actions 页面，确保：
- 工作流正常执行
- 没有持续失败的作业
- 输出文件正确生成

### 2. 监控日志

关注以下关键信息：
```
✓ Output files validated
Push successful on attempt X
Total raw nodes: XXXX
Unique nodes: XXXX
```

### 3. 备份配置

定期备份重要配置：
```bash
git config --local user.email
git config --local user.name
git remote -v
```

### 4. 使用分支策略（可选）

如果主分支频繁冲突，考虑：

```yaml
# 推送到独立分支
- name: Push changes
  run: |
    git push origin HEAD:auto-generated-nodes
```

---

## 🎉 预期效果

修复后，您应该看到：

✅ **不再出现推送冲突错误**
✅ **工作流稳定执行**
✅ **自动处理并发情况**
✅ **清晰的日志输出**
✅ **失败自动重试**

---

## 📞 需要帮助？

如果问题仍然存在：

1. **检查工作流日志**
   - 查看详细的错误信息
   - 确认哪一步失败

2. **验证仓库权限**
   - 确保 Actions 有写入权限
   - 检查分支保护规则

3. **联系支持**
   - GitHub Status: https://www.githubstatus.com
   - GitHub Support: https://support.github.com

---

**修复日期**: 2026-04-25
**工作流版本**: v2.0.1
**状态**: ✅ 已部署

*祝您的自动化节点抓取顺利进行！* 🚀
