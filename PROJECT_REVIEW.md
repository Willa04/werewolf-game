# PROJECT_REVIEW — 狼人杀 9人局

> 审查日期：2026-06-04  
> 代码行数：~999 行（单文件 HTML）  
> 提交记录：20+ commits

---

## 1. 项目概览

| 维度 | 详情 |
|------|------|
| **类型** | 纯前端单页应用 |
| **技术栈** | Vanilla JS + CSS3 + HTML5 |
| **外部依赖** | DeepSeek API（可选）、Web Speech API（浏览器内置） |
| **部署** | GitHub Pages |
| **游戏模式** | 单人 vs 8 个 AI 对手 |

## 2. 架构总览

```
index.html (999 行)
├── <style> (124 行) — CSS 变量、布局、动画、昼夜主题
├── <body> (65 行) — DOM 结构
└── <script> (807 行) — 全部游戏逻辑
    ├── 常量 & 配置 (15 行)
    ├── API Key 管理 (20 行)
    ├── 全局状态 G (15 行)
    ├── UI 辅助函数 (140 行)
    ├── 异步等待机制 (25 行)
    ├── 游戏引擎 (340 行)
    │   ├── startGame() — 初始化
    │   ├── endGame() — 强制终止
    │   ├── startRound() — 夜晚阶段
    │   ├── dayDiscussion() — 白天发言
    │   ├── votingPhase() — 投票放逐
    │   ├── checkWin() — 胜负判定
    │   └── gameOver() — 结算
    ├── AI 引擎 (135 行)
    │   ├── aiWolfTarget/aiSeerTarget/aiWitchAntidote/aiWitchPoison/aiHunterShot
    │   ├── buildPromptForPlayer() — Prompt 构造
    │   ├── callDeepSeek() — API 调用
    │   ├── aiGenerateSpeech() — 发言入口
    │   └── aiVote() — 投票决策
    ├── 语音系统 (65 行)
    └── 密码保护 (25 行)
```

## 3. 游戏状态机

```
         ┌──────────┐
         │   init   │ ← 身份确认
         └────┬─────┘
              ▼
    ┌─────────────────────┐
    │       night         │ ← 狼人→预言家→女巫→结算
    │  (startRound)       │
    └─────────┬───────────┘
              ▼
    ┌─────────────────────┐
    │        day          │ ← AI 轮流发言
    │  (dayDiscussion)    │
    └─────────┬───────────┘
              ▼
    ┌─────────────────────┐
    │       vote          │ ← 投票放逐
    │  (votingPhase)      │
    └─────────┬───────────┘
              ▼
    ┌─────────────────────┐      yes
    │    checkWin()       │────────▶ gameover
    └─────────┬───────────┘
              │ no
              ▼
         night (下一轮)
```

## 4. DeepSeek API 调用架构

```
玩家发言槽位 → aiGenerateSpeech(player)
  ├─ 检查 API Key 是否存在
  ├─ buildPromptForPlayer(player) → 构造完整 Prompt (~1500 tokens)
  │   ├─ 玩家真实身份 + 秘密信息（狼同伴/查验记录）
  │   ├─ 游戏局势（轮次/存活/出局/夜晚事件）
  │   ├─ 本轮已有发言记录
  │   ├─ 角色特定策略
  │   └─ 禁止规则（无警长/无守卫）
  ├─ callDeepSeek(prompt) → POST https://api.deepseek.com/v1/chat/completions
  │   ├─ model: deepseek-chat
  │   ├─ temperature: 0.9
  │   ├─ max_tokens: 300
  │   └─ 返回清理（去引号/去前缀/过滤违禁词）
  └─ 失败回退 → 简单模板发言
```

### Token 消耗估算

| 项目 | 数量 |
|------|------|
| Prompt 输入 / 次 | ~1,500 tokens |
| 输出 / 次 | ~300 tokens（max） |
| 每轮发言次数 | 5~9 次（存活玩家数） |
| 每局轮数 | 3~6 轮 |
| **每局总消耗** | **~30,000-50,000 tokens** |
| **每局费用** | **¥0.03-0.05** |

## 5. AI 玩家决策系统

| 角色 | 夜晚行动 | 算法 |
|------|----------|------|
| 狼人 | 选猎杀目标 | 75% 概率优先刀预言家/女巫 |
| 预言家 | 查验一人 | 随机选非自己的玩家 |
| 女巫 | 解药/毒药 | 第一晚 80% 救人；毒药 60% 概率用且**直接知道谁是狼** |
| 猎人 | 开枪带人 | 50% 概率带狼，否则随机 |
| 投票 | 白天放逐 | 狼人投好人；好人 45% 概率投狼 |

## 6. 安全机制

| 机制 | 实现 |
|------|------|
| 密码锁屏 | localStorage 存储，首次设置后需验证 |
| API Key 保护 | type="password" 输入框，localStorage 存储 |
| 游戏终止 | `G.aborted` 标志，所有 UI 函数入口检查 |
| 违禁词过滤 | Prompt + 正则双重拦截警长/守卫相关术语 |

## 7. 设计亮点

- **单一 HTML 文件**：零构建、零依赖、部署即用
- **G.aborted 全局终止**：异步安全，所有函数入口检查
- **UI 函数级别防护**：logLine/setActions/speakText/waitForClick 全部第一行检查 aborted
- **TTS 个性语音**：5 种性格对应不同 pitch/rate 参数
- **昼夜视觉切换**：星空 + 遮罩 + 光晕三层叠加，1.5s 过渡
- **卡片可点击选人**：夜晚选目标 / 投票时卡片和按钮均可操作
