# GitHub 推送前检查清单

## ✅ 已完成的准备工作

1. **代码清理**
   - [x] 移除了微博热度显示
   - [x] 所有功能正常运行（微博5条、知乎4条、HN5条）

2. **文件保护**
   - [x] 创建 `.gitignore` - 自动排除 `.env`、`__pycache__` 等敏感文件
   - [x] 创建 `LICENSE` - MIT 开源协议
   - [x] 创建 `.github/workflows/daily-brief.yml` - GitHub Actions 自动化

3. **文档更新**
   - [x] `README.md` 已包含完整使用说明
   - [x] `.env.example` 提供了配置模板

---

## 📋 推送前最后检查

### 1. 确认敏感信息已排除
```bash
# 检查 .env 是否会被提交（应该显示在 .gitignore 中）
git status --ignored
```

### 2. 初始化 Git 仓库（如果还没有）
```bash
git init
git add .
git commit -m "Initial commit: Daily Brief automation"
```

### 3. 关联远程仓库
```bash
# 替换为你的 GitHub 仓库地址
git remote add origin https://github.com/YOUR_USERNAME/daily-brief.git
git branch -M main
git push -u origin main
```

---

## 🔧 GitHub Actions 配置

推送后需要在 GitHub 仓库设置中添加 **Secrets**：

### 必需的 Secrets：
1. `NOTION_TOKEN` - 你的 Notion 集成 Token
2. `NOTION_DATABASE_ID` - Notion 数据库 ID

### 可选的 Secrets（如果需要）：
3. `DEEPSEEK_API_KEY` - AI 摘要功能
4. `BAIDU_FANYI_APP_ID` + `BAIDU_FANYI_SECRET` - 百度翻译
5. `WEIBO_API_URL` / `ZHIHU_API_URL` - 自定义 API（如果要覆盖默认）

**设置路径**：仓库页面 → Settings → Secrets and variables → Actions → New repository secret

---

## ⚠️ 重要提醒

1. **绝对不要提交 `.env` 文件** - 已在 `.gitignore` 中排除
2. **GitHub Actions 默认每天 UTC 00:00 运行**（北京时间 08:00）
3. **首次运行建议手动触发测试**：Actions 标签页 → Daily Brief → Run workflow

---

## 🚀 推送命令汇总

```bash
# 1. 初始化（如果是新仓库）
git init

# 2. 添加所有文件
git add .

# 3. 提交
git commit -m "feat: Daily Brief automation with Notion integration"

# 4. 关联远程仓库（替换为你的地址）
git remote add origin https://github.com/YOUR_USERNAME/daily-brief.git

# 5. 推送
git branch -M main
git push -u origin main
```

---

## 📌 推送后的验证步骤

1. 在 GitHub 仓库页面确认所有文件已上传
2. 检查 `.env` **没有**出现在仓库中
3. 前往 Actions 标签页，手动运行一次工作流测试
4. 在 Secrets 中添加所有必需的环境变量
5. 等待下次自动运行（或手动触发）

---

完成以上步骤后，你的 Daily Brief 就可以在 GitHub Actions 上自动运行了！
