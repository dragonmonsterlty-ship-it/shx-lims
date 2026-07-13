# 管理员添加账号设计

## 目标与边界

在现有“管理员管理”页面增加由管理员创建内网账号的能力。系统继续不提供公开注册入口；创建账号只能通过已有的管理员路由和管理员 API 完成。

不新增角色、业务对象或数据库表，不调整现有 RBAC，也不修改与用户管理无关的功能。

## 现状

- 后端 `User` 模型使用 `full_name` 作为必填显示名，密码存储字段为 `password_hash`。
- 现有角色为 `admin`、`director`、`project_manager`、`researcher`、`operator`、`viewer`。
- 登录通过 Argon2 校验密码哈希，并拒绝未启用账号。
- `/api/admin/users` 已有列表、状态、角色和重置密码操作，服务层统一执行 admin 校验。
- 用户管理菜单、页面路由和后端接口均已限制为 admin。
- 审计日志已支持 `create` 动作和 `user` 实体。

## 后端设计

新增 `POST /api/admin/users`。请求字段为：

- `username`：必填，去除首尾空白，最长 50。
- `display_name`：必填，去除首尾空白，映射到 `User.full_name`，最长 100。
- `email`：可选；空字符串归一为 `null`，非空时校验邮箱格式，最长 120。
- `password`：必填，长度 8–255。
- `role`：必填，只允许现有六种角色。
- `is_active`：默认 `true`。

服务层先执行 admin 校验，再检查用户名是否重复；重复时返回 HTTP 409 和明确消息。密码使用现有 `hash_password`。新账号设置 `must_change_password=true`。

创建用户和审计日志在同一事务提交。审计日志记录：

- `actor_user_id`、`actor_role`：由现有审计函数记录操作者。
- `action=create`、`entity_type=user`、`entity_id` 和 `target_user_id`。
- `after_data`：仅包含 `username`、`role`、`is_active`。
- `created_at`：由审计模型自动记录。

响应复用 `UserRead`，不包含密码或密码哈希。

## 前端设计

在现有 ProTable 工具栏增加主按钮“添加账号”。页面本身处于仅 admin 可访问的菜单和路由守卫中，因此非 admin 不显示入口；后端仍独立执行权限校验。

按钮打开 AntD Modal + Form，包含用户名、显示名、邮箱、初始密码、角色和启用开关。角色使用现有 `ROLE_OPTIONS`，启用默认值为 `true`。

基础校验：

- 用户名、显示名、密码和角色必填。
- 密码至少 8 位。
- 邮箱可空，填写时使用 AntD email 校验。

成功后依次关闭弹窗、重置表单、刷新 ProTable 并提示“账号创建成功”。失败时：

- 409 或用户名重复消息：将错误落到 username 字段并显示明确提示。
- 403：显示管理员权限不足提示。
- 其他错误：显示通用创建失败提示。

## 测试与验证

- 后端覆盖 admin 创建、非 admin 403、重复 username 409、响应不泄露密码、密码为哈希、审计内容及新账号登录。
- 前端服务测试覆盖 POST 请求契约。
- 页面交互测试使用现有 Vitest 环境验证打开弹窗、字段校验、提交、成功后的关闭/重置/刷新，以及关键错误提示。
- 完成后运行后端完整 pytest，以及前端 test、typecheck、lint、build；再运行仓库权威全栈验证脚本。

