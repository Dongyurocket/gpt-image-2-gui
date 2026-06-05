# gpt-image-2

调用兼容 OpenAI Images API 形式的图片接口的本地工具集，包含 Windows GUI 和 MCP 服务器两种使用方式。

支持功能：

- 文生图：`/v1/images/generations`
- 图片编辑 / 图生图：`/v1/images/edits`
- 保存 `Base URL`、`API Key`、模型、尺寸、质量、输出目录等常用参数
- 自动下载 `url` 返回的图片，或保存 `b64_json` 返回的图片
- 选择、追加、移除、清空一张或多张本地参考图片，并支持可选 PNG mask
- 支持不使用代理、使用系统代理、自定义代理；默认和推荐都是不使用代理
- 提供 MCP 服务器 (`mcp_server.py`)，把文生图和图片编辑暴露成 MCP 工具，可在支持 MCP 的客户端里直接调用

## 项目结构

```text
image2/
├── image2_gui.py        # Tkinter 桌面 GUI
├── mcp_server.py        # MCP stdio 服务器（mcp 工具入口）
├── run_gui.bat          # Windows 一键启动脚本
├── requirements.txt     # Python 依赖
├── config.example.json  # 配置文件模板（不含密钥）
├── config.json          # 本地真实配置（含 API key，已 gitignore）
└── outputs/             # 默认图片输出目录（已 gitignore）
```

## 快速开始

1. 双击 `run_gui.bat`。

   脚本会自动安装依赖，然后启动 GUI。

2. 首次使用前，把示例配置复制为本地配置：

   ```powershell
   Copy-Item config.example.json config.json
   ```

   也可以在文件管理器里把 `config.example.json` 复制一份，并重命名为 `config.json`。

3. 也可以在当前目录手动运行：

   ```powershell
   python -m pip install -r requirements.txt
   python image2_gui.py
   ```

4. 在界面顶部填写连接配置：

   - `Base URL`：你的图片 API 服务地址，例如 `https://api.example.com`
   - `API Key`：你的 Bearer 令牌，只填密钥本体，不需要写 `Bearer`
   - `Model`：模型名称，默认 `gpt-image-2`
   - `代理模式`：默认 `不使用代理`。除非你的网络环境明确要求，否则建议保持不使用代理

5. 点击 `保存配置`，或直接点击 `生成图片` / `编辑图片`。

   程序会把当前配置自动保存到同目录的 `config.json`，下次启动会自动读取。

## 修改 API Key

有两种方式：

1. 在 GUI 顶部的 `API Key` 输入框里删除旧密钥，填入新密钥。
2. 点击 `保存配置`，或直接发起一次生成/编辑请求。

保存后，`config.json` 里的 `api_key` 会更新为新密钥。`API Key` 输入框会用密码框显示，但 `config.json` 是明文文件，请不要把它发给别人。

也可以直接编辑 `config.json`：

```json
{
  "api_key": "你的新密钥"
}
```

只改这一项即可，其他配置保持原样。

## 修改 Base URL

`Base URL` 是接口服务的根地址。程序会自动根据你填写的地址拼接图片接口路径。

常见填写方式：

- 填根地址：`https://api.example.com`
- 填 `/v1` 地址：`https://api.example.com/v1`
- 填图片接口前缀：`https://api.example.com/v1/images`
- 直接填完整文生图地址：`https://api.example.com/v1/images/generations`

例如把服务地址从 A 改到 B：

1. 在 GUI 顶部 `Base URL` 输入框中填入新的服务地址。
2. 确认 `API Key` 也换成新服务对应的密钥。
3. 点击 `保存配置`。
4. 再点击 `生成图片` 测试是否能正常请求。

也可以直接编辑 `config.json`：

```json
{
  "base_url": "https://api.example.com"
}
```

## 配置文件

项目提供了一个示例配置文件：

```text
config.example.json
```

首次使用时，请复制一份并重命名为本地配置文件：

```text
config.json
```

然后在 `config.json` 里填写自己的 `base_url` 和 `api_key`，或启动 GUI 后在界面中填写并点击 `保存配置`。

当前会保存这些字段：

- `base_url`：API 服务地址
- `api_key`：Bearer 密钥，明文保存
- `model`：模型名
- `size`：图片尺寸
- `quality`：质量
- `output_format`：输出格式，`png` 或 `jpeg`
- `response_format`：返回格式，`url` 或 `b64_json`
- `output_compression`：JPEG 压缩参数
- `background`：背景参数
- `moderation`：审核参数
- `input_fidelity`：编辑接口保真度
- `output_dir`：输出目录，默认 `outputs`
- `proxy_mode`：代理模式
- `proxy_url`：自定义代理地址
- `edit_preprocess`：图片编辑前是否预处理
- `edit_max_side`：编辑上传图片最长边

`config.json` 已加入 `.gitignore`，默认不会被 Git 提交。分享项目时请使用 `config.example.json` 作为模板，不要分享自己的 `config.json`。

## 文生图

1. 打开 `文生图` 页签。
2. 在 `Prompt` 文本框输入提示词。
3. 设置尺寸、质量、输出格式等参数。
4. 点击 `生成图片`。

生成结果默认保存到 `outputs` 文件夹。界面底部会显示最近保存的文件路径，可以点击 `打开目录` 查看。

## 图片编辑 / 图生图

1. 打开 `图片编辑 / 图生图` 页签。
2. 点击 `选择图片`，选择本地 `png`、`jpg`、`jpeg` 或 `webp` 参考图片。
3. 普通用户建议一次只上传 1 张参考图，接口更稳定，也更容易让模型理解要保留的主体和风格。
4. 如果确实需要多张参考图，可以在文件选择窗口里多选，或点击 `追加图片` 继续添加。
5. `选择图片` 会替换当前参考图列表；`追加图片` 会保留已有图片并继续添加；`移除选中` 和 `清空图片` 可用于整理列表。
6. 如果接口需要 mask，点击 `选择Mask` 选择 PNG mask；不需要时留空。
7. 在 `Prompt` 文本框输入编辑要求。
8. 点击 `编辑图片`。

图片编辑默认可开启预处理，把上传副本缩小到 `上传最长边` 以内，减少接口超时概率。预处理只会生成临时副本，不会改动原图。

## 参数说明

- `n` 固定为 `1`，程序不会发送多图数量。
- `stream`、`partial_images`、`style` 不会发送。
- 只有 `output_format` 为 `jpeg` 时才会发送 `output_compression`。
- 图片编辑接口会用 `multipart/form-data` 上传本地图片；单张参考图使用 `image` 字段，多张参考图使用多个 `image[]` 字段。
- 虽然 GUI 支持多张参考图，但仍建议优先只上传 1 张；多张图片会增加上传体积、超时概率和提示词歧义。
- `response_format=url` 时程序会下载 URL 图片；`response_format=b64_json` 时程序会解码保存图片。

## 代理设置

建议尽量不要开启代理，优先使用 `不使用代理`。图片生成和下载通常耗时较长，代理会增加连接失败、超时、下载中断等不稳定因素。

只有在你的网络环境明确无法直连接口时，再考虑使用系统代理或自定义代理。如果看到类似 `ProxyError('Unable to connect to proxy')` 的报错，说明请求被代理影响，但代理没有正常响应。

可以在界面里这样处理：

- 普通直连：选择 `不使用代理`，这是推荐设置
- 必须走系统代理：选择 `使用系统代理`
- 必须指定代理：选择 `自定义代理`，并填写例如 `http://127.0.0.1:7890`

## 服务器断开连接

如果看到类似 `RemoteDisconnected('Remote end closed connection without response')`，说明已经连到目标服务器，但服务器或上游网关在返回结果前断开了连接。

图片编辑更容易遇到这个问题。建议先这样重试：

- `编辑预处理`：`开启`
- `上传最长边`：`1024`
- `质量`：`medium`
- `尺寸`：`1024x1024`
- `代理模式`：`不使用代理`
- Prompt 先写短一点，确认能通后再逐步提高质量和尺寸

## MCP 服务器

`mcp_server.py` 通过 [Model Context Protocol](https://modelcontextprotocol.io/) stdio 接口，把 image2 的能力暴露成两个 MCP 工具，**配置仍然由 GUI 维护**（`config.json`），MCP 只读取，不在协议层管理密钥。

### 依赖

MCP 服务器除了 GUI 的依赖，还需要：

```text
mcp[cli]>=1.0.0
```

`requirements.txt` 已经包含这一行。

### 启动

在项目根目录下手动启动：

```powershell
python mcp_server.py
```

stdio 模式会一直阻塞等待客户端输入，不能直接在终端里运行出"完成"效果，正确的做法是把它注册到 MCP 客户端的配置里。

### 注册到 MCP 客户端

下面是几个常见客户端的配置示例。`command` 用项目里 Python 解释器，`args` 指向 `mcp_server.py` 绝对路径。占位符 `<PROJECT_ROOT>` 替换成你本机实际项目根目录，例如 `C:/Users/yourname/Downloads/image2`。

Claude Desktop (`claude_desktop_config.json`)：

```json
{
  "mcpServers": {
    "image2": {
      "command": "python",
      "args": ["<PROJECT_ROOT>/mcp_server.py"]
    }
  }
}
```

Proma / 其他支持 `mcp.json` 的客户端：

```json
{
  "servers": {
    "image2": {
      "command": "python",
      "args": ["<PROJECT_ROOT>/mcp_server.py"]
    }
  }
}
```

修改配置后重启 MCP 客户端，新工具就会出现在工具列表里。

### 可用工具

| 工具名 | 用途 | 关键参数 |
| --- | --- | --- |
| `generate_image` | 文生图 | `prompt` |
| `edit_image` | 图片编辑 / 图生图 | `prompt`, `image_paths`（绝对路径列表，至少 1 张）, `mask_path`（可选 PNG mask 绝对路径） |

两个工具都会返回生成文件的绝对路径。模型、尺寸、质量、输出格式等参数仍然从 `config.json` 读取，不在工具签名里暴露。

### 配置要求

调用任一工具时，服务器会读取 `config.json`：

- `base_url` 不能为空，也不能仍是默认占位
- `api_key` 不能为空

如果还没在 GUI 里保存过配置，工具调用会以 `RuntimeError` 形式返回明确报错，提示先在 GUI 里填写并保存。不会因为缺配置就静默走默认占位 URL。

### 注意事项

- MCP 服务器和 GUI 共用 `config.json`，所以密钥、上游地址、代理等都由 GUI 维护；MCP 端不要另外写密钥，避免配置漂移。
- `image_paths` 和 `mask_path` 必须是本地绝对路径。MCP 客户端传入相对路径时，工具会直接报错而不是静默拼接。
- 图片编辑接口默认走 `multipart/form-data`；单张参考图使用 `image` 字段，多张使用 `image[]` 字段。和 GUI 行为完全一致。
- `image_paths` 中文件类型必须是 PNG / JPG / JPEG / WebP，否则会被 `guess_mime` 拒绝。
- 工具调用是同步的，单次请求最长等待 `API_TIMEOUT_SEC`（600 秒）。如果上游处理慢，客户端可能需要等较长时间才返回路径。
