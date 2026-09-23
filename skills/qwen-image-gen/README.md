# Qwen Image Gen

[简体中文](README.md) | [English](README.en.md) · [返回 Craft Skills](../../README.md)

**让已经部署的 Qwen-Image 更好地理解你想画什么、想改哪里。**

海报把“不要二维码”也印成了文字？想换姿势却只换了衣服？设置了高清尺寸，返回的图仍然很小？这个 Skill 将创作需求落实为提示词、参考图关系、画幅参数和原图验收，并把质量反馈带回下一次生成。

**v0.3.0 实验版。** 当前 Agent 负责改写；不需要再下载提示词增强模型。包内提供可选的本地 ComfyUI Qwen Image 2.1 文生图客户端，仍需用户已有模型和运行中的 ComfyUI。

## 样张与提示词

| 天台绿裙 | 草莓蛋糕写真 | 黑白夜归 |
| --- | --- | --- |
| [![天台绿裙](assets/examples/portraits/rooftop-green.png)](assets/examples/portraits/rooftop-green.png) | [![草莓蛋糕写真](assets/examples/portraits/strawberry-cake.png)](assets/examples/portraits/strawberry-cake.png) | [![黑白夜归](assets/examples/portraits/noir-portrait.png)](assets/examples/portraits/noir-portrait.png) |
| [复制提示词](assets/examples/portraits/rooftop-green.txt) | [复制提示词](assets/examples/portraits/strawberry-cake.txt) | [复制提示词](assets/examples/portraits/noir-portrait.txt) |

以上为本地 Qwen-Image 文生图样张，均为 **1152×2048**，人物为虚构成年人。点击图片查看大图；[参数与文件记录](assets/examples/portraits/manifest.json)。它们展示题材与画面效果，提示词改写对照见下方。

## 能帮你做什么

| 你的需求 | Skill 的处理方式 |
| --- | --- |
| 文生图、海报文字 | 锁定主体、动作和逐字文案，将说明性限制与画面文字分开 |
| 局部改图 | 明确改哪里、改成什么，以及其余需要保留的内容 |
| 换姿势、换场景 | 区分参考人物与原构图，允许肩膀、四肢、衣物随新动作变化 |
| 同人物系列 | 从通过验收的身份参考出发，每张一个动作，分别给出完整提示词 |
| 自动选择画幅 | 根据内容建议比例，再转成后端真正接受的尺寸参数 |
| 质量问题重做 | 区分结构缺陷和审美偏好，保留原图与修正版进行比较 |

## 安装与第一次使用

以下为 Codex 首次安装示例；已有同名目录时先备份自己的修改。

```sh
git clone https://github.com/ZSeven-W/craft-skills.git
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R craft-skills/skills/qwen-image-gen "${CODEX_HOME:-$HOME/.codex}/skills/"
```

重新加载 Agent 会话后，用 `$qwen-image-gen` 调用。其他支持 Skill 的 Agent 可将该目录放入其技能目录。**只要提示词就不需要生图连接**；要求实际生成时，需提供已有 Qwen 工作流的连接方式，密钥通过本地配置管理，不写入提示词或仓库。

**先写提示词：**

```text
使用 $qwen-image-gen，把我的柠檬茶海报需求整理成提示词。
只出现“夏日柠檬茶”“¥19”两行文字，3:4。先给提示词，不生成。
```

```text
使用 $qwen-image-gen，先看参考图，把人物转成正面站姿。
保留人物身份、服装和环境，允许肩部、手臂和褶皱随动作变化。
```

**生成同人物系列：**

```text
使用 $qwen-image-gen，以这张照片作为人物身份参考，生成三张独立的咖啡馆写真：
正面坐姿、窗边侧身、站着端杯。保留同一人物，每张一个动作，9:16。
用我已配置的 Qwen 工作流生成，并保存每张的实际提示词、参数和原图。
```

## 改写前后：从实际失败出发

| 中文海报：原提示词 | 中文海报：改写后 |
| --- | --- |
| [![原提示词海报](assets/examples/ab/poster-A.png)](assets/examples/ab/poster-A.png) | [![改写后海报](assets/examples/ab/poster-B.png)](assets/examples/ab/poster-B.png) |

| 打开柜门取玻璃罐：原提示词 | 打开柜门取玻璃罐：改写后 |
| --- | --- |
| [![改写前取罐动作](assets/examples/ab/reach-A.png)](assets/examples/ab/reach-A.png) | [![改写后取罐动作](assets/examples/ab/reach-B.png)](assets/examples/ab/reach-B.png) |

研究阶段用已有语言模型加公开的 Qwen PE 模板，固定种子、步数、画布与参考图，只替换提示词。四组观察：海报目标文字更准确、面包师双脚完整入镜、取罐空间关系改善；**反坐高脚椅仍未完成**。[四组原图与条件](assets/examples/ab/README.md) · [两版提示词与参数](assets/examples/ab/cases.json)。

这些是形成 Skill 的研究样例，不是最终 Skill 的通用胜率证明，也不是官方 PE 权重的复现。当前包通过 22 项代码测试和 8 个离线 Agent 试用案例；新的成图级 Skill 对照仍待补充。

## 工作方式与接入

需求 → 判断文生图 / 局部编辑 / 参考创作 → 改写与画幅决策 → 已有 Qwen 工作流 → 原图验收 → 带缺陷反馈修正。

提示词改写默认由当前 Agent 完成；看参考图时需要视觉理解能力。无需额外下载大模型。普通使用者直接调用 Skill；应用开发者可选用离线请求构建器或共享运行模块。

本地 ComfyUI 文生图可使用 `scripts/run_comfyui.py`。它会预检节点和模型、提交 API 工作流、跟踪同一任务 ID，并可通过 `/view` 下载原图；服务地址可用 `COMFYUI_URL` 或 `--server` 配置。详见 [本地 ComfyUI 接入](references/comfyui-local.md)。

## 文档与边界

- [完整中文指南](../../docs/qwen-image-gen.zh-CN.md)
- [Agent 工作流](SKILL.md)
- [研究 A/B 原图与参数](assets/examples/ab/README.md)
- [人像原图与提示词](assets/examples/portraits/README.md)
- [测试与边界](../../evals/qwen-image-gen/VALIDATION.md)
- [可选应用集成：共享运行模块](references/shared-runtime.md)（Node.js 18+，不联网）

可选脚本 `scripts/prepare_workbench_request.py` 只在本地构造一种工作台协议的请求，不联网、不改写、不生成。其单参考图、约1MP编辑和2048像素上限属于适配器，不能推导为 Qwen 模型的上限。

官方 PE 权重和系统提示词全文不在包内。复杂肢体、人物一致性和工作流参数仍要实际看图验收。
