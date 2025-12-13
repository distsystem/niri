# Known Issues

## niri IPC SetWindowWidth 不生效

### 问题描述

通过 socket IPC 直接调用 `SetWindowWidth` action 返回 `{"Ok":"Handled"}`，但窗口宽度实际上没有改变（变成 0% 或不变）。

### 环境

- niri 版本：25.11 (b35bcae)
- 脚本期望版本：25.08 (af4b5f9)

### 测试过程

1. **直接 socket IPC 调用**：
   ```json
   {"Action":{"SetWindowWidth":{"id":121,"change":{"SetProportion":0.5}}}}
   ```
   返回 `{"Ok":"Handled"}`，但窗口宽度不变。

2. **SetColumnWidth 同样不生效**：
   ```json
   {"Action":{"SetColumnWidth":{"change":{"SetProportion":0.5}}}}
   ```
   返回 `{"Ok":"Handled"}`，窗口变成 0% 宽度。

3. **添加延迟无效**：在调用前添加 50ms 延迟，问题依旧。

4. **命令行调用正常**：
   ```bash
   niri msg action set-window-width --id 121 50%
   ```
   工作正常，窗口宽度正确设置。

### 当前解决方案

使用 `subprocess` 调用 `niri msg` 命令行工具，而非直接 socket IPC：

```python
def set_window_width(window_id: int, width: str):
    subprocess.run(["niri", "msg", "action", "set-window-width", "--id", str(window_id), width])
```

### 可能原因

1. niri 25.11 版本的 IPC 格式可能有变化
2. Python socket 发送和 niri msg CLI 发送的 JSON 可能有细微差异
3. 时序问题：窗口创建后立即设置宽度可能被 niri 布局引擎覆盖

### 待调查

- 对比 `niri msg` 实际发送的 socket 数据
- 检查 niri 25.11 的 changelog 是否有 IPC 变更
- 使用 strace 捕获 `niri msg` 的 socket 通信内容
