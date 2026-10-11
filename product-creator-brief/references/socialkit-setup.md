# SocialKit API 配置教程

技能支持使用 SocialKit 搜索话题与下载参考视频。你只需配置一次 Access Key，之后可以用中文提出采集与 Brief 任务，不用自己写 API 请求。安装技能包本身不会配置 Key。配置后用 check 命令核对认证与余额；付费搜索和下载按具体任务执行。

## 1. 拿到 Access Key

打开 [SocialKit](https://www.socialkit.dev/)，注册或登录。进入项目的 **Access Keys** 页面，复制 Access Key；网站导航若变化，以 [官方入门](https://docs.socialkit.dev/getting-started) 为准。是否有试用额度、套餐价格和是否需要充值，看你账户当时显示的内容。

API Key 相当于让本地脚本使用你 SocialKit 项目额度的通行证。它不是 Instagram 密码；当前匿名话题搜索不需要登录你的 Instagram。不要把 Key 发到聊天、公开文档或 GitHub。

## 2. 在 Mac 终端保存 Key

打开 macOS 的“终端”，逐行复制下面两条命令。将 `/path/to/your/project` 替换为你的项目目录后，再运行；技能脚本路径采用 macOS 上的默认安装位置。

```bash
cd /path/to/your/project
python3 "${CODEX_HOME:-$HOME/.codex}/skills/product-creator-brief/scripts/socialkit.py" configure
```

看到 `SocialKit Access Key（输入不显示）:` 后，粘贴 Key，再按回车。粘贴时不显示字符是正常的。看到“Key 已保存到本地私有文件”即保存完成；这一步不会调用 API。

Key 保存在当前项目 `work/private/socialkit.json`，文件权限为仅自己可读写。它没有放进技能目录或 ZIP 包。每个 API 请求由脚本放入 `x-access-key` 请求头，你不需要手动设置。认证方案见 [官方认证说明](https://docs.socialkit.dev/authentication)。

如果 `python3` 显示 command not found，把这条错误告诉 Codex；先检查现有运行环境，再决定是否需要安装 Python，不必自己盲目安装其他库。这个脚本只用 Python 标准库。

## 3. 检查连接与额度

在同一个终端执行：

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/product-creator-brief/scripts/socialkit.py" check
```

预期输出类似：

```json
{"authentication": "ok", "remaining_credits": 100}
```

100 只是示例，以实际返回的剩余额度为准。检查认证与余额不会发起搜索或下载，不消耗采集积分；免费认证检查依据见 [官方 Skills 说明](https://docs.socialkit.dev/skills)。`authentication: ok` 表示 Key 可用；如果额度为 0，需要在网站按你的需求选择额度，再发起采集。请只反馈成功／错误码，不发送 Key 文件。

配置后回到这个聊天说：“Key 已配置，帮我检查连接。”Codex 就能运行无扣费检查，并继续你已要求的任务。

## 4. 直接这样使用

第一次小样本试用：

> 使用 $product-creator-brief，搜索 Instagram 上 product review 话题，最多下载 3 条与我本次产品相关的视频，每条最长 2 分钟、480p。搜索最多 1 积分、下载最多 6 积分。分析开头、演示、叙事和 CTA，结合我提供的产品资料与参考风格，给我 3 个不同方向及对应英文达人 Brief，再为最合适的方向写音画脚本。

只需找参考、不下载：

> 搜索我提供的话题，给我本次返回的参考视频清单、来源和筛选理由，先不下载、不转写。

已有链接，不再付搜索费：

> 下载我给你的这 2 个 Instagram Reels 链接，每条最多 120 秒、480p、下载上限 4 积分，分析后为我提供的产品做达人 Brief。链接：……

只写 Brief：

> 不采集新素材。根据我提供的产品资料与参考视频风格，写 3 个方向的英文 Brief。

## 5. 看懂额度与搜索范围

当前规则核对于 2026-10-06：一次成功话题搜索用 1 积分，一次最多返回 12 条，只提供这一批，不保证覆盖整个话题。详情见 [搜索接口](https://docs.socialkit.dev/api-reference/instagram-reels-search-api)。

480p 视频按每开始一分钟 1 积分计费，720p／1080p 按每开始一分钟 4 积分计费；例如 61 秒的 480p 视频为 2 积分。默认 3 条、每条最长 120 秒，下载保守预留 6 积分，加一次搜索最多预留 7 积分。转写是额外功能，默认不调用付费转写。下载费用依据见 [官方文档](https://docs.socialkit.dev/api-reference/async-download-api)。

如果你说“多找几个方向”，技能不会自动把它理解成大量付费搜片。要扩大采集可指定“搜 3 个词，下载 5 条，总预算多少积分”。当前 Python 下载命令的 `--max-credits` 只控制下载；搜索预算由技能另行按次数控制。

## 6. 常见问题与换项目

| 看到的错误／状态 | 怎么处理 |
|---|---|
| `key_missing` | 回到上述项目目录，再执行 configure；或提供已有 Key 文件路径 |
| `401`／`403` 无效 Key | 去 Access Keys 核对或换 Key，再运行 configure；不要贴 Key 给 Codex |
| `403` 提示浏览器标识被拦截 | 这是服务防护层错误，不能直接判为 Key 无效；当前脚本已设置明确的 API 客户端标识。让 Codex 检查响应来源，不反复更换 Key |
| `insufficient_credits` | 网站补充额度后继续原任务，不重复提交下载 |
| `pending`／`poll_timeout` | 视频还没处理完；请 Codex 用相同目录和参数续查原任务 |
| `failed`／`content_unavailable` | 本条失败，查看公开可访问性或换参考片；不是已经下载成功 |
| `submission_unknown` | 请求结果不确定，先查后台／联系支持找回 job_id；不要反复提交 |
| `batch_credit_cap_reached` | 批次保守预算不足；请 Codex解释已用预留量并按新范围安排，不能静默加预算 |
| `download_not_mp4` | 返回的不是可识别 MP4；保留任务记录，排查服务返回内容 |

在其他项目使用时，告诉 Codex：“沿用原项目的本地 Key 文件，内容不要输出。”脚本可以这样指定路径（`--key-file` 放在子命令前）：

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/product-creator-brief/scripts/socialkit.py" --key-file /path/to/your/project/work/private/socialkit.json check
```

有 `SOCIALKIT_API_KEY` 环境变量时它优先于文件；已采用文件配置就不必再配置环境变量。更换 Key 时确认是否还有旧环境变量覆盖，否则文件更新不会生效。

成片与研究记录默认放执行任务的项目里，Key 始终独立保存。素材用于风格观察和创意参考；如需把他人的片段放进品牌发布内容，需要另有使用授权。
