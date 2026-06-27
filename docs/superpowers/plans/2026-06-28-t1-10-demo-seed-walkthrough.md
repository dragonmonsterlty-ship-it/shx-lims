# T1.10 Demo Seed & Browser Walkthrough Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提供受保护、可重复的本地演示数据库重建与 seed 流程，并给出按角色组织的浏览器验收路径。

**Architecture:** PowerShell 入口只负责环境保护、显式确认、Alembic 重建和调用 Python seed。Python seed 复用现有基础数据，并通过现有 service/API 工作流生成可演示的样品、检测任务、结果及真实审计事件；测试在临时 SQLite 数据库验证稳定资产，文档负责人工附件操作。

**Tech Stack:** PowerShell 5.1、Python 3、FastAPI、SQLAlchemy、Alembic、pytest、PostgreSQL。

---

### Task 1: Seed 资产契约测试

**Files:**
- Create: `backend/tests/test_demo_seed.py`
- Modify: `backend/scripts/seed_demo.py`

- [ ] **Step 1: 写临时数据库失败测试**

测试调用公开 seed 入口两次，断言规范账号、两个隔离项目、草稿和已完成样品、待处理与已批准检测链、日报多 items，以及实验/日报/样品真实审计事件存在。

- [ ] **Step 2: 验证测试因缺少新 seed 行为失败**

Run: `$env:TEST_DATABASE_URL='sqlite+pysqlite:///:memory:'; .\.venv\Scripts\python.exe -m pytest tests/test_demo_seed.py -q`

Expected: FAIL，缺少完成样品、已批准检测链或审计事件。

- [ ] **Step 3: 最小扩展 seed**

保留现有账号和基础资料 helper；新增公开的 demo workflow helper，使用现有 service/API 状态入口创建和推进演示实体，不改业务模块。

- [ ] **Step 4: 验证目标测试通过**

Run: `$env:TEST_DATABASE_URL='sqlite+pysqlite:///:memory:'; .\.venv\Scripts\python.exe -m pytest tests/test_demo_seed.py -q`

Expected: PASS。

### Task 2: 受保护的本地重建入口

**Files:**
- Create: `scripts/seed-demo.ps1`
- Test: `backend/tests/test_demo_seed.py`

- [ ] **Step 1: 增加入口资产失败测试**

断言脚本要求 `-Force`，包含本地 host/端口与 demo/dev 数据库名保护，并明确输出破坏性警告。

- [ ] **Step 2: 验证资产测试失败**

Run: `$env:TEST_DATABASE_URL='sqlite+pysqlite:///:memory:'; .\.venv\Scripts\python.exe -m pytest tests/test_demo_seed.py -q`

Expected: FAIL，入口文件不存在。

- [ ] **Step 3: 实现 PowerShell 入口**

读取后端当前配置，拒绝非 `localhost`/`127.0.0.1`、非允许本地端口或疑似生产库；无 `-Force` 只打印警告并中止；通过后依次执行 Alembic downgrade/upgrade 和 seed。

- [ ] **Step 4: 验证资产测试通过**

Run: `$env:TEST_DATABASE_URL='sqlite+pysqlite:///:memory:'; .\.venv\Scripts\python.exe -m pytest tests/test_demo_seed.py -q`

Expected: PASS。

### Task 3: Demo 文档

**Files:**
- Create: `docs/demo-walkthrough.md`
- Modify: `README.md`
- Test: `backend/tests/test_demo_seed.py`

- [ ] **Step 1: 增加文档契约失败测试**

断言文档包含 seed 命令、启动命令、账号表、三类角色路径、附件操作和 `verify:api` 污染提示。

- [ ] **Step 2: 验证测试失败**

Run: `$env:TEST_DATABASE_URL='sqlite+pysqlite:///:memory:'; .\.venv\Scripts\python.exe -m pytest tests/test_demo_seed.py -q`

Expected: FAIL，文档不存在。

- [ ] **Step 3: 编写 walkthrough 并链接 README**

文档明确仅限本地 demo/dev、`-Force` 的破坏性含义、正式演示前重新 seed，以及 admin/project_manager/analyst 的人工路径。

- [ ] **Step 4: 验证目标测试通过**

Run: `$env:TEST_DATABASE_URL='sqlite+pysqlite:///:memory:'; .\.venv\Scripts\python.exe -m pytest tests/test_demo_seed.py -q`

Expected: PASS。

### Task 4: 完整验收与提交

**Files:**
- Verify only: all T1.10 files

- [ ] **Step 1: 按用户指定顺序运行前端四项**
- [ ] **Step 2: 运行完整后端 pytest**
- [ ] **Step 3: 运行 `scripts/verify-fullstack.ps1`**
- [ ] **Step 4: 对运行中的本地后端运行 `npm.cmd run verify:api`**
- [ ] **Step 5: 用 `scripts/seed-demo.ps1 -Force` 重建并验证 demo 数据**
- [ ] **Step 6: 运行 `git diff --check` 与 `git status --short`**
- [ ] **Step 7: 仅暂存 T1.10 文件并提交**

Run: `git commit -m "chore: add demo seed walkthrough"`

Expected: 提交成功，`CLAUDE.md` 仍保持未暂存修改。
