# Executor 实施计划

## 目标

实现 `executor/` 模块，让它成为唯一持有并操作 `MinecraftSim` 的运行时。修改main.py：简短代码实例化env，手动调用各个tools函数。

在本地实现完毕后推送到ssh hitsz-ssh 上运行，位置：/mnt/home/user42/ChillyHigh/SpacialMine/SpacialMine

核心约束：

- `MinecraftSim.step()` 只能由 `Executor` 调用。
- 同一时间只允许一个 Handler 操作 env。
- LLM 发起 env 操作时，如果 executor 正忙，立即返回失败 `Result`，不排队。
- `craft` 只能在 crafting GUI 已打开时执行，`smelt` 只能在 furnace GUI 已打开时执行。
- `open_crafting_table` / `open_furnace` 负责打开对应 GUI，并更新 executor 内部 GUI 状态。
- env 要启动一个独立的 WebSocket server 旁路推送画面和信息；server 不等待客户端连接，只管发，也不影响 executor 主流程。
- Minestudio / Java / Malmo / 渲染相关异常原样抛出，不做自定义异常包装。
- 内部只调用一次的短 helper 不拆函数，直接内联。

## 交付文件

```text
executor/
├── __init__.py
├── types.py
├── base.py
├── executor.py
├── craft.py
├── smelt.py
├── open_gui.py
├── place.py
├── dig.py
├── navigate.py
├── steve.py
└── ws.py
```

## 1. 类型定义

先实现 `executor/types.py`。

需要的类型：

- `GameSnapshot`
- `Result`
- `ExecutorStatus`
- `BackgroundTask`

`Result` 是 executor 唯一结果类型：

```python
@dataclass(frozen=True)
class Result:
    success: bool
    action_type: str
    status: Literal["started", "done", "failed", "cancelled"]
    task_id: str | None
    steps_taken: int | None
    failure_reason: str | None
    smelt_task: BackgroundTask | None
```

语义：

- 同步成功：`success=True`, `status="done"`, `steps_taken` 为实际步数。
- 异步启动成功：`success=True`, `status="started"`, `task_id` 非空，`steps_taken=None`。
- 业务失败或 executor 忙：`success=False`, `status="failed"`, `failure_reason` 非空。
- 异步取消：`success=False`, `status="cancelled"`。

## 2. Handler 契约

实现 `executor/base.py`。

```python
class AbstractHandler(ABC):
    action_type: ClassVar[str]
    is_async: ClassVar[bool]

    @abstractmethod
    def run(self, env: MinecraftSim, params: dict) -> Result:
        ...
```

规则：

- Handler 不创建 env。
- Handler 不保存 env。
- Handler 不捕获 Minestudio 系统异常。
- Handler 只把可恢复业务失败转成 `Result(success=False, status="failed", ...)`。
- Handler 参数由 tool 层和 executor 调用点保证，不在多层重复校验。

## 3. Executor 主体

实现 `executor/executor.py`。

职责：

- 设置 `MINESTUDIO_DIR`。
- 创建唯一 `MinecraftSim`。
- 调用 `reset()` 初始化环境。
- 维护 `latest_snapshot`。
- 维护 `gui_state`，记录 crafting / furnace / inventory GUI 是否打开。
- 串行执行同步 Handler。
- 启动和管理唯一异步 Handler。
- 维护 `ExecutorStatus` 和 `background_tasks`。
- 启动一个独立的 WebSocket server 旁路，持续推送最新画面和关键信息。
- `shutdown()` 调用 `MinecraftSim.close()`。

初始化要求：

```python
os.environ.setdefault("MINESTUDIO_DIR", "/mnt/home/user42/ChillyHigh/minestudio_data")
self.env = MinecraftSim(
    action_type="env",
    obs_size=config.env_obs_size,
    seed=config.env_seed or 0,
    preferred_spawn_biome=config.env_preferred_biome,
)
```

不要在这里检查 engine 是否存在。`MinecraftSim` 自己会处理并报错。
WebSocket server 也在这里启动，但它是独立旁路，不等待客户端连接，也不阻塞 executor 的创建和 reset。

## 4. submit 语义

`submit(handler, params) -> Result` 是 executor 的核心接口。

同步 Handler：

1. 如果已有异步任务 running，返回忙失败。
2. 设置当前状态为 running。
3. 直接调用 `handler.run(self.env, params)`。
4. 更新 `last_result`。
5. 更新 `latest_snapshot`。
6. 返回 `Result`。

异步 Handler：

1. 如果已有任务 running，返回忙失败。
2. 生成 `task_id`。
3. 设置当前状态为 running。
4. 启动后台线程。
5. 立即返回 `Result(success=True, status="started", task_id=...)`。
6. 后台线程结束后写入 `last_result`，更新状态为 done / failed / cancelled。

忙失败的 `failure_reason` 要明确，例如：

```text
executor is busy: current task dig_to_level is running; call check_executor or cancel_task first
```

## 5. 快照更新

`GameSnapshot` 从 `MinecraftSim` 的 `obs` 和 `info` 构造。
WebSocket server 直接发送最新 `GameSnapshot` 和关键 executor 状态，是非阻塞旁路，不参与 executor 的同步流程。

更新时机：

- `reset()` 后更新一次。
- 每个 Handler 内部每次 `env.step()` 后更新。
- 同步 Handler 结束后确保再发布一次最新快照。
- 异步 Handler 结束后确保再发布一次最新快照。

不要为了快照再包一层 environment 模块。

## 6. 同步 Handler

优先实现这些同步 Handler：

- `CraftHandler`
- `SmeltHandler`
- `OpenCraftingTableHandler`
- `OpenFurnaceHandler`
- `PlaceBlockHandler`

同步 Handler 必须在返回前完成动作或明确失败。

GUI 规则：

- `CraftHandler` 对 3x3 配方只能在 crafting table GUI 已打开时执行。
- `CraftHandler` 对 2x2 背包配方不要求先打开 crafting table；若没有 GUI，handler 会打开 inventory GUI 后合成；若 crafting table GUI 已打开，则直接在 crafting table GUI 合成。
- `SmeltHandler` 只能在 furnace GUI 已打开时执行。
- `OpenCraftingTableHandler` 成功后把 crafting GUI 状态置为已打开。
- `OpenFurnaceHandler` 成功后把 furnace GUI 状态置为已打开。
- 关闭或切换 GUI 时，executor 要同步更新 GUI 状态，不能让状态漂移。

`open_*` 当前语义：

- MineStudio 官方 `MinecraftSim(action_type="env")` 暴露的是按键/鼠标动作和 `voxels` 查询，不提供“自动寻找最近 crafting table / furnace 并走过去打开”的高级接口。
- 因此第一版 `open_crafting_table` / `open_furnace` 的契约是：调用前玩家视角必须已经对准对应方块；handler 只执行 `use` 并检查 `isGuiOpen`。
- 自动定位、转向、导航到附近 crafting table / furnace 需要后续基于 `voxels` 单独实现，不能在第一版里 silent fallback 或假装完成。

GUI 操作实现：

- 本项目内置 MineStudio recipe/tag assets 到 `assets/`，运行时只读取本仓库文件。
- GUI slot 坐标和鼠标操作在 `executor/gui.py` 中维护。
- `executor/gui.py` 的所有环境推进都必须走 Executor 绑定的 `step` 回调，不能直接绕过 `Executor` 调用 `MinecraftSim.step()`。

`smelt` 特殊规则：

- 只负责把矿石放进熔炉。
- 不等待熔炼完成。
- 调用前必须先打开 furnace GUI。
- 成功后返回带 `smelt_task` 的 `Result`。
- Executor 收到 `smelt_task` 后加入 `background_tasks`。

## 7. 异步 Handler

实现这些异步 Handler：

- `DigHandler`
- `NavigateHandler`
- `SteveHandler`

异步 Handler 只允许一个运行中。

取消规则：

- `cancel_task()` 设置取消标记。
- Handler 每轮 step 前检查取消标记。
- 取消后返回 `Result(success=False, status="cancelled", ...)`。
- 不强杀线程。

## 8. Tool 接入

`agent/tools.py` 只调用 executor。

同步工具：

```python
result = executor.submit(CraftHandler(config), {"item": item, "count": count})
if not result.success:
    raise ToolException(result.failure_reason)
return f"craft {item} x{count} done"
```

异步工具：

```python
result = executor.submit(DigHandler(config), {"target_y": target_y})
if not result.success:
    raise ToolException(result.failure_reason)
return f"dig_to_level started: {result.task_id}"
```

Tool 不直接访问 `MinecraftSim`。

## 9. 验证顺序

按风险逐步验证：

1. `python -m py_compile` 编译 executor 模块。
2. 远程 import `MinecraftSim`。
3. 远程创建 `Executor` 并 `reset`。
4. 执行一次 no-op step，确认 `latest_snapshot` 更新。
5. 启动 ws server，确认即使没有客户端连接也持续推送。
6. 执行一个 `craft` / `smelt`，在未打开 GUI 时确认明确失败。
7. 执行 `open_crafting_table` / `open_furnace` 后，再执行对应同步 handler，确认返回 `Result(status="done")`。
8. 启动一个异步 Handler，确认立即返回 `Result(status="started")`。
9. 异步运行中再次 submit，确认忙失败且不排队。
10. `cancel_task()`，确认最终状态为 cancelled。
11. `shutdown()`，确认 Minecraft 进程关闭。

## 10. 暂不实现

以下内容不要在 executor 第一版实现：

- 多任务队列。
- 多 env。
- 进程池。
- dispatcher。
- environment 包装层。
- 自动 fallback 到其他 Minecraft 启动方式。
- Neo4j graph 写入。
