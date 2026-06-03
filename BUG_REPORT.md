# BUG_REPORT — 狼人杀 9人局

> 审查日期：2026-06-04  
> 基于：index.html (999 行)

---

## 🐛 Bug 清单

### BUG-1 【严重】AI 女巫拥有上帝视角

**位置**：`aiWitchPoison()` 函数

**代码**：
```js
const suspects=alivePlayers().filter(p=>R[p.roleKey].camp==='wolf');
```

**问题**：AI 女巫直接按真实身份筛选狼人来毒杀。真实游戏中女巫应该靠推理判断谁是狼，而不是直接查数据库。

**影响**：AI 女巫 100% 准确毒杀狼人，严重破坏游戏平衡。

**建议**：AI 女巫应基于发言记录、投票历史、被怀疑次数等线索推断，而非读内存。

---

### BUG-2 【中等】DeepSeek API 无超时处理

**位置**：`callDeepSeek()` 函数

**代码**：
```js
const resp=await fetch(DEEPSEEK_API,{...});
```

**问题**：`fetch` 没有设置超时（AbortController）。如果 API 无响应，游戏永久卡在"AI生成中"。

**建议**：添加 15 秒超时，超时后回退到备用发言。
```js
const ctrl = new AbortController();
setTimeout(() => ctrl.abort(), 15000);
fetch(url, {signal: ctrl.signal, ...});
```

---

### BUG-3 【中等】预言家查验记录未关联具体玩家

**位置**：`buildPromptForPlayer()` 中的 seerChecks

**问题**：当人类是预言家时，`G.seerChecks` 记录了人类的所有查验。但当人类不是预言家、AI 是预言家时，AI 预言家的查验也记录在同一个数组中。如果人类某局游戏中不是预言家，`G.seerChecks` 仍然包含上一局（或其他预言家）的查验记录。

实际上检查代码：
```js
G.seerChecks.push({round:G.round, targetId:seerTarget, isWolf:...});
```
在 `buildPromptForPlayer` 中：
```js
if(player.roleKey==='SEER'&&G.seerChecks.length>0){
  G.seerChecks.forEach(c=>{...});
}
```
AI 预言家会看到所有历史查验记录，包括人类预言家之前查验的记录。应该按预言家身份过滤。

**建议**：seerChecks 中增加 `seerId` 字段，查询时按 `player.id` 过滤。

---

### BUG-4 【轻微】`lastGuardTarget` 字段冗余

**位置**：全局状态 `G`

**代码**：
```js
nightTargets: { wolf:null, seer:null, guard:null },
lastGuardTarget: null,
```

**问题**：守卫角色不存在，`guard` 和 `lastGuardTarget` 字段从未使用，增加认知负担。

**建议**：移除或留待守卫角色实现时再添加。

---

### BUG-5 【中等】平票规则可导致多人同时出局

**位置**：`votingPhase()` 函数

**代码**：
```js
else if(eliminated.length>1){
  eliminated.forEach(id=>{ G.players[id-1].alive=false; ... });
}
```

**问题**：平票时所有平票玩家全部出局。标准狼人杀规则通常是平票无人出局或进行第二轮发言。

**影响**：极端情况下 3+ 人同时出局，可能直接触发游戏结束，略显不自然。但这可以是设计选择。

**建议**：保持或改为平票无人出局。

---

### BUG-6 【轻微】`systemSay` / `deathSay` 未直接检查 `G.aborted`

**位置**：`systemSay()`, `deathSay()` 函数

**代码**：
```js
function systemSay(msg){ logLine(msg, 'system'); }
function deathSay(msg){ logLine(msg, 'death'); }
```

**问题**：这两个函数依赖 `logLine()` 内部的 `G.aborted` 检查。但如果未来 `logLine` 被修改移除了检查，这两个函数就会漏过。作为防御性编程，直接加检查更安全。

**建议**：在 `systemSay` 和 `deathSay` 中也加 `if(G.aborted) return;`。

---

### BUG-7 【轻微】AI 狼人选目标时可能选已死玩家

**位置**：`aiWolfTarget()` 函数

**代码**：
```js
const targets = alivePlayers().filter(p=>R[p.roleKey].camp!=='wolf');
```

**问题**：当狼人仅剩 1 只且其他存活玩家为 0 个好人（不会出现，因为 checkWin 会触发），或者所有存活玩家都是狼人阵营时（也不可能），理论上安全。但 `alivePlayers()` 过滤了 `p.alive`，所以不会选到已死玩家。

**结论**：实际上没有问题，`alivePlayers()` 已过滤。误报。

---

### BUG-8 【轻微】`temperature: 0.9` 偏高

**位置**：`callDeepSeek()` 

**代码**：
```js
body: JSON.stringify({..., temperature:0.9, max_tokens:300})
```

**问题**：温度 0.9 较高，可能导致 AI 发言不稳定、偶尔跑偏。建议 0.7-0.8。

**建议**：降至 0.75。

---

### BUG-9 【轻微】首轮发言无上下文

**位置**：`buildPromptForPlayer()` 

**问题**：第一轮白天发言时，所有玩家都是第一个发言（因为没有之前的发言记录）。但实际上，发言是按编号顺序进行的。第一个发言的玩家（1号或最小存活编号）确实没有上下文，但后续发言的玩家应该能看到前面人的发言。

检查 `dayDiscussion`：发言按 `speakers` 顺序进行，每人口述后 `G.roundSpeeches.push(...)`。后续发言者在 `buildPromptForPlayer` 中可以看到之前的发言。**逻辑正确，非 Bug**。

---

## 统计

| 严重度 | 数量 |
|--------|------|
| 严重 | 1 |
| 中等 | 3 |
| 轻微 | 4 |
| 误报 | 2 |

## 优先级修复建议

1. **BUG-1**：AI 女巫上帝视角 → 最影响游戏体验，优先修
2. **BUG-2**：API 超时 → 影响游戏稳定性
3. **BUG-3**：预言家记录泄露 → 影响 AI 角色扮演
4. **BUG-5**：平票规则 → 可选调整
5. **BUG-8**：温度调整 → 低成本改进
