"""
狼人杀自动测试脚本 — Playwright 驱动
运行 10 局，查找 Bug，输出报告
"""
import asyncio
import json
import time
import re
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:3000/index.html"
TEST_ROUNDS = 10

results = []  # 每局结果
bugs = []     # 发现的 Bug
console_errors = []  # 控制台错误

async def run_one_game(browser, game_num):
    """运行一局完整游戏，返回结果字典"""
    global console_errors
    game_log = {
        "game_num": game_num,
        "human_role": None,
        "human_id": None,
        "result": None,
        "rounds_played": 0,
        "errors": [],
        "stuck": False,
        "timeout_events": [],
    }

    ctx = await browser.new_context(
        storage_state={
            "origins": [{
                "origin": "http://localhost:3000",
                "localStorage": [
                    {"name": "werewolf_access_pw", "value": "test123"},
                    {"name": "werewolf_owner_set", "value": "1"},
                ]
            }]
        }
    )
    page = await ctx.new_page()

    # 监听控制台错误
    page.on("console", lambda msg: (
        console_errors.append(f"[Game {game_num}] {msg.type}: {msg.text}")
        if msg.type == "error" else None
    ))

    try:
        # 1. 打开页面
        await page.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        await asyncio.sleep(0.5)

        # 2. 输入密码解锁
        lock_input = page.locator("#lockInput")
        if await lock_input.is_visible():
            await lock_input.fill("test123")
            await page.locator(".lock-box .btn-accent").click()
            await asyncio.sleep(0.5)

        # 3. 静音（避免 TTS 延迟）
        mute_btn = page.locator("#btnMute")
        if await mute_btn.is_visible():
            await mute_btn.click()
            await asyncio.sleep(0.3)

        # 4. 点击"开始游戏"
        start_btn = page.locator("#actionButtons .btn-start")
        await start_btn.click()
        await asyncio.sleep(1.0)

        # 5. 获取人类玩家身份
        prompt_text = await page.locator("#actionPrompt").text_content()
        # 格式: "🎭 你的身份：🔮 预言家（3号）"
        role_match = re.search(r'身份：(.+?)（(\d+)号）', prompt_text)
        if role_match:
            game_log["human_role"] = role_match.group(1).strip()
            game_log["human_id"] = int(role_match.group(2))
        print(f"  🎭 Game {game_num}: {game_log['human_id']}号 — {game_log['human_role']}")

        # 6. 点击"确认身份，开始游戏"
        confirm_btn = page.locator("#btnStartGame")
        if await confirm_btn.is_visible(timeout=3000):
            await confirm_btn.click()
        else:
            game_log["errors"].append("确认身份按钮未出现")
            game_log["stuck"] = True
            return game_log

        # 7. 主游戏循环：自动通过所有阶段
        max_steps = 80  # 最多80步，防止死循环
        step = 0
        idle_steps = 0  # 连续空闲步数
        while step < max_steps:
            step += 1
            await asyncio.sleep(0.4)

            # 检查是否游戏结束
            phase_icon = await page.locator("#phaseIcon").text_content()
            action_text = await page.locator("#actionPrompt").text_content()

            if "🏁" in phase_icon or "游戏结束" in action_text:
                log_text = await page.locator("#logArea").text_content()
                if "狼人阵营获胜" in log_text:
                    game_log["result"] = "wolf_win"
                elif "好人阵营获胜" in log_text:
                    game_log["result"] = "good_win"
                round_match = re.findall(r'第 (\d+) 轮', log_text)
                if round_match:
                    game_log["rounds_played"] = int(round_match[-1])
                restart_btn = page.locator("#btnRestart")
                if await restart_btn.is_visible(timeout=2000):
                    await restart_btn.click()
                    await asyncio.sleep(0.5)
                break

            clicked = False

            # 优先级1：人类发言输入
            speech_input = page.locator("#textInput")
            if await speech_input.is_visible(timeout=100):
                try:
                    await speech_input.fill("我觉得需要仔细分析一下大家的发言，看看谁最可疑。")
                    await page.locator("#btnSend").click(timeout=1000)
                    clicked = True
                    idle_steps = 0
                    await asyncio.sleep(0.3)
                    continue
                except:
                    pass

            # 优先级2：跳过语音
            skip_speech = page.locator("#btnSkipSpeech")
            if await skip_speech.is_visible(timeout=100):
                try:
                    await skip_speech.click(timeout=1000)
                    clicked = True
                    idle_steps = 0
                    await asyncio.sleep(0.3)
                    continue
                except:
                    pass

            # 优先级3：确认/救人类按钮
            accent_btn = page.locator("#actionButtons .btn-accent")
            if await accent_btn.first.is_visible(timeout=100):
                try:
                    await accent_btn.first.click(timeout=1000)
                    clicked = True
                    idle_steps = 0
                    await asyncio.sleep(0.3)
                    continue
                except:
                    pass

            # 优先级4：可选择的玩家卡片
            selectable_card = page.locator(".player-card.selectable")
            if await selectable_card.first.is_visible(timeout=100):
                try:
                    await selectable_card.first.click(timeout=1000)
                    clicked = True
                    idle_steps = 0
                    await asyncio.sleep(0.3)
                    continue
                except:
                    pass

            # 优先级5：跳过按钮
            skip_btn = page.locator("#actionButtons .btn-skip")
            if await skip_btn.first.is_visible(timeout=100):
                try:
                    await skip_btn.first.click(timeout=1000)
                    clicked = True
                    idle_steps = 0
                    await asyncio.sleep(0.3)
                    continue
                except:
                    pass

            # 优先级6：危险按钮（狼人选目标/投票）
            danger_btn = page.locator("#actionButtons .btn-danger:not([disabled])")
            cnt = await danger_btn.count()
            if cnt > 0:
                try:
                    await danger_btn.first.click(timeout=1000)
                    clicked = True
                    idle_steps = 0
                    await asyncio.sleep(0.3)
                    continue
                except:
                    pass

            # 优先级7：普通操作按钮
            action_btn = page.locator("#actionButtons .btn-action:not([disabled])")
            cnt2 = await action_btn.count()
            if cnt2 > 0:
                try:
                    await action_btn.first.click(timeout=1000)
                    clicked = True
                    idle_steps = 0
                    await asyncio.sleep(0.3)
                    continue
                except:
                    pass

            # 没找到可点击的→等待（夜晚AI决策/发言阶段）
            if not clicked:
                idle_steps += 1
                # 连续空闲>30步，可能是卡死
                if idle_steps > 30:
                    game_log["stuck"] = True
                    game_log["errors"].append(f"连续空闲{idle_steps}步，可能卡死")
                    # 截图保存
                    await page.screenshot(path=f"f:/项目/Claude狼人杀/stuck_game_{game_num}.png")
                    break
                await asyncio.sleep(0.3)

        else:
            # 超时
            game_log["stuck"] = True
            game_log["errors"].append(f"超过 {max_steps} 步，卡死")
            print(f"  ⚠️ Game {game_num}: 卡死了！")

        # 检查控制台错误
        game_errors = [e for e in console_errors if f"Game {game_num}" in e]
        for e in game_errors:
            if "error" in e.lower() or "fail" in e.lower():
                game_log["errors"].append(f"Console: {e}")

    except Exception as e:
        game_log["errors"].append(f"Exception: {str(e)[:200]}")
        print(f"  ❌ Game {game_num}: 异常 - {str(e)[:100]}")
    finally:
        await ctx.close()

    return game_log


async def main():
    print("=" * 60)
    print("🐺 狼人杀自动测试 — Playwright")
    print(f"   测试局数: {TEST_ROUNDS}")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for i in range(1, TEST_ROUNDS + 1):
            print(f"\n▶ Game {i}/{TEST_ROUNDS}...")
            start_time = time.time()
            result = await run_one_game(browser, i)
            elapsed = time.time() - start_time
            result["duration_sec"] = round(elapsed, 1)
            results.append(result)
            status = "✅" if result["result"] and not result["stuck"] else "❌"
            print(f"  {status} {result['result'] or 'stuck'} | {result['rounds_played']}轮 | {elapsed:.1f}s")

        await browser.close()

    # ========== 生成报告 ==========
    generate_report()


def generate_report():
    print("\n" + "=" * 60)
    print("📊 测试报告")
    print("=" * 60)

    # 统计
    completed = [r for r in results if r["result"] is not None]
    stuck = [r for r in results if r["stuck"]]
    errors = [r for r in results if r["errors"]]

    print(f"\n总测试局数: {len(results)}")
    print(f"正常完成: {len(completed)}")
    print(f"卡死/异常: {len(stuck)}")
    print(f"有错误: {len(errors)}")

    if completed:
        wolf_wins = sum(1 for r in completed if r["result"] == "wolf_win")
        good_wins = sum(1 for r in completed if r["result"] == "good_win")
        avg_rounds = sum(r["rounds_played"] for r in completed) / len(completed)
        print(f"\n狼人胜: {wolf_wins} | 好人胜: {good_wins}")
        print(f"平均轮数: {avg_rounds:.1f}")

    # 角色分布
    roles = {}
    for r in completed:
        role = r.get("human_role", "unknown")
        roles[role] = roles.get(role, 0) + 1
    print(f"\n角色分布: {json.dumps(roles, ensure_ascii=False)}")

    # 错误汇总
    all_errors = []
    for r in results:
        for e in r.get("errors", []):
            all_errors.append(f"Game {r['game_num']}: {e}")

    if all_errors:
        print(f"\n⚠️  错误汇总 ({len(all_errors)} 条):")
        for e in all_errors[:20]:
            print(f"  - {e[:150]}")

    # 写入报告文件
    report_path = Path("f:/项目/Claude狼人杀/TEST_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 狼人杀自动测试报告\n\n")
        f.write(f"> 测试时间：{time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"> 测试局数：{len(results)}\n")
        f.write(f"> 完成率：{len(completed)}/{len(results)} ({100*len(completed)//len(results)}%)\n\n")

        f.write("## 摘要\n\n")
        f.write(f"| 指标 | 值 |\n|------|-----|\n")
        f.write(f"| 总局数 | {len(results)} |\n")
        f.write(f"| 正常完成 | {len(completed)} |\n")
        f.write(f"| 卡死 | {len(stuck)} |\n")
        f.write(f"| 狼人胜 | {sum(1 for r in completed if r['result']=='wolf_win')} |\n")
        f.write(f"| 好人胜 | {sum(1 for r in completed if r['result']=='good_win')} |\n")
        if completed:
            f.write(f"| 平均轮数 | {sum(r['rounds_played'] for r in completed)/len(completed):.1f} |\n")
        f.write(f"| 平均耗时 | {sum(r['duration_sec'] for r in results)/len(results):.1f}s |\n\n")

        f.write("## 每局详情\n\n")
        f.write("| # | 角色 | ID | 结果 | 轮数 | 耗时 | 状态 |\n")
        f.write("|---|------|----|------|------|------|------|\n")
        for r in results:
            status = "✅" if r["result"] and not r["stuck"] else "❌"
            f.write(f"| {r['game_num']} | {r.get('human_role','?')} | {r.get('human_id','?')} | {r.get('result','stuck')} | {r.get('rounds_played',0)} | {r.get('duration_sec',0)}s | {status} |\n")

        if all_errors:
            f.write("\n## 错误日志\n\n")
            for e in all_errors:
                f.write(f"- {e}\n")

    print(f"\n📄 报告已保存: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
