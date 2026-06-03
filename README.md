# gpt-image-2-gui

这是一个 Windows 本地 GUI 调用工具，用来调用兼容 OpenAI Images API 形式的图片接口。

支持功能：

- 文生图：`/v1/images/generations`
- 图片编辑 / 图生图：`/v1/images/edits`
- 保存 `Base URL`、`API Key`、模型、尺寸、质量、输出目录等常用参数
- 自动下载 `url` 返回的图片，或保存 `b64_json` 返回的图片
- 选择本地图片和可选 PNG mask
- 支持不使用代理、使用系统代理、自定义代理

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
   - `代理模式`：默认 `不使用代理`

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
2. 点击 `选择图片`，选择本地 `png`、`jpg`、`jpeg` 或 `webp` 图片。
3. 如果接口需要 mask，点击 `选择Mask` 选择 PNG mask；不需要时留空。
4. 在 `Prompt` 文本框输入编辑要求。
5. 点击 `编辑图片`。

图片编辑默认可开启预处理，把上传副本缩小到 `上传最长边` 以内，减少接口超时概率。预处理只会生成临时副本，不会改动原图。

## 参数说明

- `n` 固定为 `1`，程序不会发送多图数量。
- `stream`、`partial_images`、`style` 不会发送。
- 只有 `output_format` 为 `jpeg` 时才会发送 `output_compression`。
- 图片编辑接口会用 `multipart/form-data` 上传本地图片。
- `response_format=url` 时程序会下载 URL 图片；`response_format=b64_json` 时程序会解码保存图片。

## 代理设置

如果看到类似 `ProxyError('Unable to connect to proxy')` 的报错，说明请求被代理影响，但代理没有正常响应。

可以在界面里这样处理：

- 普通直连：选择 `不使用代理`
- 必须走系统代理：选择 `使用系统代理`
- 必须指定代理：选择 `自定义代理`，并填写例如 `http://127.0.0.1:7890`

## 服务器断开连接

如果看到类似 `RemoteDisconnected('Remote end closed connection without response')`，说明已经连到目标服务器，但服务器或上游网关在返回结果前断开了连接。

图片编辑更容易遇到这个问题。建议先这样重试：

- `编辑预处理`：`开启`
- `上传最长边`：`1024`
- `质量`：`medium`
- `尺寸`：`1024x1024`
- Prompt 先写短一点，确认能通后再逐步提高质量和尺寸
