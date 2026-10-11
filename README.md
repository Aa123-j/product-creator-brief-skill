# Product Creator Brief

**产品创意与达人 Brief**：根据使用者提供的产品资料和真实达人样本，输出多方向创意、合作 Brief 及可拍摄的短视频脚本。

## 功能

- 多方向创意：区分观看动机、场景与证明路径。
- 达人适配：分析开场、表达、镜头、互动与商业植入。
- Brief 与脚本：中文策略，英文 Brief、口播、字幕与分镜；可按任务调整语言。
- 素材研究：使用 SocialKit，在明确预算与数量范围内搜索和下载 Instagram 参考视频。

内容策划支持 Instagram、TikTok、YouTube；当前采集脚本支持 Instagram。公开版本只提供通用流程，不包含预置品牌产品、真实达人案例或具体产品效果。使用时在自己的项目中提供资料。

## 安装与入口

完整技能目录为 [`product-creator-brief/`](product-creator-brief)。将该目录安装到技能目录并保留目录名。Codex 默认位置为 `~/.codex/skills/`；自定义 `CODEX_HOME` 时使用其 `skills/` 目录。

- [技能入口](product-creator-brief/SKILL.md)
- [产品资料整理](product-creator-brief/references/product-line.md)
- [证据与表达](product-creator-brief/references/claims.md)
- [SocialKit 配置](product-creator-brief/references/socialkit-setup.md)
- [交付规格](product-creator-brief/references/deliverables.md)
- [上游方法与接口来源](product-creator-brief/references/sources.md)

## 使用示例

**多方向完整交付**

> 使用 $product-creator-brief。产品资料、达人账号与代表视频如下：……。平台 Instagram。请分析真实风格，给三个不同方向，每个方向都输出英文 Brief、完整分镜、口播和 Caption。不要采集新素材。

**有预算的素材研究**

> 根据我提供的产品与话题搜索参考视频，最多下载三条、每条最长120秒、480p。搜索最多1积分，下载最多6积分。分析后给三个创意方向及对应 Brief。

**只写 Brief**

> 根据本次产品资料，为三个不同内容方向写达人 Brief，并说明各自的匹配理由，不展开完整脚本。

仅写 Brief 或分析已有视频无需 SocialKit Key。资料、密钥、下载文件和任务记录保存在使用者的项目中，不随公开技能发布。API 说明标注核对日期，调用时按服务当时规则执行。

方法参考 Motion、Aaron Marketing Skills、Social Media Skills 与 SocialKit 的相关技能，采用独立编写的整合实现；详见[来源说明](product-creator-brief/references/sources.md)。
