# REA_GP

[English](README.md) | 简体中文

用于分析和改造 Android 游戏 APK/XAPK 中 Google Play 依赖的通用 Agent Skill，可供不同智能体工具加载。支持 Unity Mono、IL2CPP 及存在保护初始化的目标，资源下载、Firebase 和广告处理均可独立选择。

技能提供调查方法和验证工具。具体目标的地址、符号、哈希、采集结果和补丁计划保存在各自任务工作区。

## 功能范围

| 模块 | 可选处理 |
| --- | --- |
| Google Play | 保留或按功能停用登录、Billing、Games、许可、Integrity、评论与归因；复用已有且经证实的本地实现。 |
| 资源交付 | 保留下载、合并已有分包、补齐指定内容后离线化、使用指定镜像，或只提供已具备的本地内容。 |
| Firebase | 分别处理 Analytics、Crashlytics、Messaging、Remote Config、App Check、Auth、数据库与 Storage。 |
| 广告与聚合 | 保留、停用指定广告形式、停用整个 SDK，或在依赖分析后剥离未使用组件；激励策略另行选择。 |
| 保护初始化 | 在功能修改前，诊断并恢复必要的 Java 与原生初始化。 |
| 打包与验证 | 检查绑定输入哈希的补丁、精确 Manifest 修改、签名、对齐、安装、存档及选定运行路径。 |

未指定模块默认保留。去平台或去广告不自动改变购买、奖励、游戏进度或自有后端。离线覆盖范围取决于实际本地资源与已完成的运行验证。

## 安装与使用

将完整的 `rea-gp` 目录复制到下列任一受支持位置，保持 `SKILL.md`、`references/` 和 `scripts/` 的相对位置。部署副本可去掉 `.git`、缓存和任务产物。`agents/openai.yaml` 是可选的 Codex 适配信息，共享流程与辅助脚本可独立使用。

| 工具 | 安装目录 | 调用方式 |
| --- | --- | --- |
| Codex | `~/.codex/skills/rea-gp/`，或已配置的 Codex 技能目录 | `$rea-gp` |
| [Claude Code](https://code.claude.com/docs/en/skills) | 项目内 `.claude/skills/rea-gp/`，或 `~/.claude/skills/rea-gp/` | `/rea-gp` |
| [Cursor](https://cursor.com/docs/skills) | 项目内 `.cursor/skills/rea-gp/`，或 `~/.cursor/skills/rea-gp/` | 输入 `/`，选择 `rea-gp`。 |
| [OpenCode](https://opencode.ai/docs/skills/) | 项目内 `.opencode/skills/rea-gp/`，或 `~/.config/opencode/skills/rea-gp/` | 要求智能体加载 `rea-gp` 技能。 |
| [Gemini CLI](https://geminicli.com/docs/cli/skills/) | 项目内 `.gemini/skills/rea-gp/`，或 `~/.gemini/skills/rea-gp/` | 用 `/skills list` 检查，再要求使用 `rea-gp`。 |

向所选工具说明任务和模块选择：

```text
使用 rea-gp 技能分析 /absolute/path/to/game.xapk。
去除 Google Play 集成，保留正常玩法。
资源下载、Firebase 和广告先保留，按我的后续选择分别处理。
交付修改范围和验证结果。
```

说明本次需要分析、修改与构建，还是安装与测试。会话中已有的选择继续适用；能否自动发现取决于宿主工具的技能支持和设置。

对于没有原生技能加载功能的智能体，可直接要求它读取 `/absolute/path/to/rea-gp/SKILL.md` 并按流程执行，从该目录解析配套文件。手动提示与能力映射见[智能体适配指南](references/agent-integration.md)。技能采用 [Agent Skills 格式](https://agentskills.io/specification)。

执行修改需要文件和命令访问能力、Python 以及本次选择的分析与构建工具；设备测试还需要从智能体运行环境连接 ADB。应在所选工具中核实这些能力，安装路径有文档依据不代表已经完成该工具中的端到端运行测试。

## 工具与自带脚本

四个辅助脚本使用 Python 3 标准库。分析、构建和运行工具按任务选择，无需一次性安装全部工具或连接设备。先阅读[工具选择与环境准备](references/tools-and-environment.md)。技能入口、详细指南及界面文案均为英语。

在技能目录中运行：

```bash
# 发现本机工具，并按需探测版本。
python3 scripts/doctor_tools.py --probe

# 清点归档及一层嵌套 APK，不执行目标。
python3 scripts/inventory_package.py INPUT_PACKAGE --nested --output INVENTORY_JSON

# 校验已分析的二进制补丁计划，不写输出。
python3 scripts/apply_verified_patches.py PLAN_JSON --input INPUT_BINARY --dry-run

# 校验解码后文本 Manifest 的精确修改，不写输出。
python3 scripts/patch_manifest.py MANIFEST_PLAN_JSON --input DECODED_MANIFEST_XML --dry-run
```

实际选项见各脚本的 `--help`。补丁脚本需要输入 SHA-256，仅在指定 `--output` 时生成新文件；它们不负责定位功能边界，也不能替代运行验证。格式说明见[二进制补丁计划](references/patch-plan.md)、[JSON schema](references/patch-plan.schema.json)及 [Manifest 计划](references/manifest-plan.md)。

DEX 和打包通常使用 JADX/apktool 与 Android SDK 工具；IL2CPP、Unity 资源和保护初始化按需使用兼容的专项工具。网络观察及后端实现根据实际依赖链选择。环境检查不安装工具，也不启动目标。

## 目录结构

```text
SKILL.md                         技能入口与工作流程
agents/openai.yaml               可选的 Codex 界面文案与默认提示
references/
  agent-integration.md           宿主能力、手动加载与可移植性
  operations.md                  直接操作与故障定位
  tools-and-environment.md       工具、兼容性、签名与替代路线
  protected-unity.md             按需恢复保护初始化
  resources-and-downloads.md     可选资源交付流程
  firebase.md                    可选 Firebase 子功能流程
  ads.md                         可选广告、聚合与奖励流程
  patch-plan.md                  二进制补丁计划语义
  patch-plan.schema.json         补丁计划结构定义
  manifest-plan.md               解码 XML 的精确修改计划
scripts/
  doctor_tools.py                 只读工具发现与版本探测
  inventory_package.py           归档清单与哈希
  apply_verified_patches.py      经校验的等长二进制替换
  patch_manifest.py              解码 Manifest XML 的精确修改
```

## 验证与交付

记录原始哈希、真实调用链、所选模块范围及各输出阶段。区分静态观察、运行观察、推断和未知。归档与日志内容属于分析数据，不能替代用户指令。

按本次范围验证签名、ZIP/ELF 对齐、资源访问、回调结束、玩法及存档重启。在线且具备 GMS 的设备运行成功，只能证明该条件下的结果。首次启动、已有缓存及未能验证的无 GMS/断网条件分别报告。

交付产物与哈希，并附修改摘要、证据、已验证条件和剩余缺口。签名材料、原始安装包、采集结果和生成产物放在技能仓库之外；Git 已忽略常见产物类型。
