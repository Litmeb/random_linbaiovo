# 茶话会随机生成 / random_tea_party

**本分支为茶话会特供**。一个「猜发帖人」小游戏：从茶话会的帖子中随机抽一条，显示标题和正文，让你在两名作者里猜是谁发的。赛博风界面，带积分、排行榜与历史统计。

## 功能概览

- **出题**：从 `hot_posts.json` 随机取一条帖子，展示标题 + 正文；两个选项为一正一扰，干扰项随机抽取。题库是前四百条回复数超过超过50的帖子，大概到2025-11-28之后
- **计分**：答题过程中每秒 -1 分；答对 +10，答错 -10；支持暂停、重开，可清除「历史最高」记录（不影响已上传排行榜与 delete token）。
- **统计**：正确数、错误数、正确率；当前最高分、历史最高分。
- **排行榜**：使用 Firebase Firestore，可上传历史最高分（含正确率、正答数、时间），按总分 → 正确率 → 正答数排序；可输入名字、查看榜单、删除自己上传的记录（他人不可删）。
- **本地记忆**：历史最高分、上次排行榜使用的「你的名字」会保存在浏览器本地。

## 如何运行

1. 用本地 HTTP 服务打开（否则无法加载 `hot_posts.json` 和 Firebase），例如：
   ```bash
   python -m http.server 8080
   ```
2. 浏览器访问 `http://localhost:8080/index.html`，点击「开始游戏」即可。

排行榜需配置 Firebase，详见 [FIREBASE_SETUP.md](FIREBASE_SETUP.md)。

## 数据来源与爬虫

题目数据来自 `posts.json`，可由本仓库自带的 Bangumi 小组爬虫生成。

### Bangumi 小组爬虫

`bgm_group_crawler.py` 会抓取指定 Bangumi 小组的讨论帖，输出包含 `author`、`title`、`url`、`body` 的 JSON。

### 使用方式

```bash
python bgm_group_crawler.py https://bgm.tv/group/boring --pages 999 --limit 400 --output hot_posts.json --min-replies 50
```

选项说明：
- `--pages`：抓取列表页数（默认 1）
- `--limit`：最多抓取的帖子数量
- `--sleep`：请求间隔秒数（默认 1.0）
- `--output`：输出 JSON 路径（默认 `posts.json`）
- `--min-replies`：过滤回复数过少的帖子

将生成的 `posts.json` 放在与 `index.html` 同目录下即可被游戏读取。

## 项目结构

- `index.html` — 游戏前端（单页，含样式与脚本）
- `hot_posts.json` — 题目数据（作者、标题、正文、链接等）
- `bgm_group_crawler.py` — Bangumi 小组帖子爬虫
- `FIREBASE_SETUP.md` — Firebase Firestore 排行榜配置说明
