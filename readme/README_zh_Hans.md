# Seedance by Ace Data Cloud：CrewAI 独立原生工具

由 **Ace Data Cloud** 提供，不是 Seedance 或 CrewAI 官方产品。独立品牌工具包，不是通用服务合集。[English](../README.md)

## 安装

源码/预览包正在准备，尚未PyPI发布、尚未进入CrewAI官方Tools/AMP目录。先检查[源码PR](https://github.com/AceDataCloud/SeedanceCrewAI/pulls)，用审阅后的固定完整SHA安装，不把仓库或本地导入当官方收录：

```bash
uv add 'crewai-seedance @ git+https://github.com/AceDataCloud/SeedanceCrewAI.git@REVIEWED_COMMIT'
```

正式PyPI发布后目标为 `uv add crewai-seedance`，目前不要假设可用。Python3.10–3.13；Intel macOS可能缺CrewAI强制依赖lancedb wheel，正式使用选择受支持Linux，不跳依赖伪装正常安装。

## 注册登录、General application和专用Token

1. 打开 [Ace Applications](https://platform.acedata.cloud/console/applications?utm_source=github&utm_medium=referral&utm_campaign=evergreen&utm_content=seedancecrewai_readme_zh_api_key)，注册并登录。必要时初始化General application。
2. 打开General application，确认Seedance权限、当前[模型价格和余额](https://platform.acedata.cloud/models?utm_source=github&utm_medium=referral&utm_campaign=evergreen&utm_content=seedancecrewai_readme_zh_pricing)；服务专属应用只可使用对应授权服务。
3. 点击下图1复制已有Key，或2 **Manage Keys → Create** 创建 `Seedance CrewAI` 专用Key。

![真实Key复制和Manage Keys入口，凭据已遮挡](../assets/tutorial/get-api-key-en.png)

4. 按需设过期、额度限制。Allowed APIs启用时同时允许 `/seedance/videos`、`/seedance/tasks`。

![创建专用Key的真实历史截图](../assets/tutorial/create-api-key-en.png)

2026-10-18从SunoDify固定SHA `8d3d03570e73324220f111f7fe343da0792a8071` 原样复用。第二图历史名字Dify tutorial只是例子，这里填 `Seedance CrewAI`；没有可见真实凭据。[来源](../assets/tutorial/source.json)。

将原始API消费者Token安全写入环境变量 `ACEDATACLOUD_API_KEY`，不加Bearer/空格/引号，不用platform管理Token，不写prompt、截图或提交.env。可由密钥存储传入api_key参数，序列化不包含它。

## CrewAI粘贴位置与具名工具

```python
from crewai import Agent
from seedance_crewai import SeedanceGenerateVideoTool, SeedanceRetrieveTaskTool

agent = Agent(
    role="Seedance制作助手",
    goal="按已批准额度生成，并查询原任务结果",
    backstory="通过Ace Data Cloud使用Seedance",
    llm=your_configured_llm,
    tools=[SeedanceGenerateVideoTool(), SeedanceRetrieveTaskTool()],
    allow_delegation=False,
    max_retry_limit=0,
)
```

Key放环境变量，工具加入Agent的tools列表，无需MCP。工具名为 **Seedance by Ace Data Cloud - Generate Video / Retrieve Task**。仅添加不调用；实际付费由使用者批准。每个生成实例默认一次使用，防止重复提交，但不是资金上限/授权系统。

## 服务差异、首用与异步同ID查询

结构化 `content`：文本、图片URL（首帧/尾帧/参考图角色）、音频URL（reference_audio）、视频URL（reference_video）。分辨率为小写 `480p/720p/1080p/4k`；可选 ratio、duration -1..30、frames、seed、camerafixed、watermark、generate_audio、return_last_frame。模型决定能力和合法组合，不隐式猜测。未暴露搜索、回调、过期、优先级或管理字段。

[当前目录](https://platform.acedata.cloud/models?utm_source=github&utm_medium=referral&utm_campaign=evergreen&utm_content=seedancecrewai_readme_zh_first_use)决定可用模型/组合和价格，模型ID原样传递，不自动fallback。下面是固定合同的示例，不是永久默认；**真实执行生成收费，本教程未执行**：

```python
import json
from seedance_crewai import SeedanceGenerateVideoTool, SeedanceRetrieveTaskTool

parameters = {
    "model": "doubao-seedance-2-0-mini-260615",
    "content": [
        {
            "type": "text",
            "text": "A calm sunrise over a mountain lake"
        }
    ],
    "resolution": "480p",
    "ratio": "16:9",
    "generate_audio": false
}
# 执行会收费，须先批准模型和额度。
submitted = SeedanceGenerateVideoTool().run(**parameters)
submitted = json.loads(submitted)  # 先处理可能的ToolFailure，不能直接当成功。
result = SeedanceRetrieveTaskTool().run(task_id=submitted["task_id"], wait_seconds=240)
print(result)
```

生成只提交一次async=true，accepted/pending不是成功，即使外层success=true也不例外。保存原task_id，未完成/超时/结果不明时先查历史，不重新生成。等待只查询同一ID，有界等待还可能包含在途请求的超时。终态必须有finished_at、服务success及目标媒体URL；嵌套失败和终态缺媒体不当成功。

查询自己已有任务的免费例子：

```bash
uv run python examples/query_existing.py YOUR_EXISTING_TASK_ID
```

实际查询 `POST /seedance/tasks`、action=retrieve、id=原ID；输出status/success/task_id/media_urls/原cost（Credits，不是USD或新账单）。不返回原prompt/请求、账户应用身份或原始诊断；URL存在不代表已验证长期可播放。

## 查看工具执行

![CrewAI官方历史真实界面，仅作交互参考，非Ace本包运行](../assets/tutorial/official-crewai-tracing.png)

[官方tracing参考](https://docs.crewai.com/en/observability/tracing)，2026-10-18取回，图中10/1/2025日期标记、版本未注明。左为执行步骤，右只展开Response；**非本包运行、非Ace调用、不承诺新GUI**。可选trace账号/认证/同意须由用户依官方规则完成，本包不启用。真实截图不要泄露Key/私人媒体。

## 常见问题

| 情况 | 处理 |
|---|---|
| 401/403 | 检查完整消费者Token、过期、服务授权、Allowed APIs与余额；403不一概等于审核。 |
| 400/本地schema失败 | 用本服务的字段、大小写及模型组合；错误跨服务字段联网前拒绝。 |
| pending/无结果 | 只查询原ID，不重新生成。 |
| 429 | 降并发等待；工具HTTP不自动重试，LLM/agent本身可能另有重试。 |
| 超时/5xx | 提交可能已到服务端，先查历史再决定是否重发。 |
| ToolFailure | 失败或终态缺正确媒体，结构化默认不可重试；联系支持用task/trace ID，别交Key。 |
| 媒体打不开 | 核终态与网络；不把URL存在当播放验收。 |

代码免费，媒体与配置的LLM按当前价格计费；无支付处理器/自动收费重试/fallback。原Credits费用按当前应用套餐折扣，不硬编码旧美元换算。不把安装/测试数当注册或收入。prompt/参考素材与Token仅发往api.acedata.cloud；本包无追踪，CrewAI/LLM设置另算。[隐私](../PRIVACY.md) · [源码](https://github.com/AceDataCloud/SeedanceCrewAI) · [反馈](https://github.com/AceDataCloud/SeedanceCrewAI/issues) · dev@acedata.cloud

开发：uv sync --group dev；uv run pytest；uv run ruff check .；uv build。测试Mock收费HTTP，真实Agent/Task/Crew使用本地确定性模型，不冒充真实AI决策。合同固定来源见tests/contract-source.json。
