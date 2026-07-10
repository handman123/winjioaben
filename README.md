# GameDataKeeper v2.0 — 云电脑游戏数据持久化助手

一键备份/恢复 Steam 登录凭证和游戏存档，专为云电脑场景设计。

## 适用场景

- 租用云电脑玩 Steam 游戏，每次会话结束数据被清空
- Steam 每次都要重新扫码登录
- 游戏存档需要手动备份到持久数据盘

## 快速开始

### 获取 EXE

从 [GitHub Releases](../../releases) 下载 `GameDataKeeper.exe`（每次 push 到 main 分支自动构建）。

### 首次使用

1. 把 `GameDataKeeper.exe` 放到数据盘（如 `Q:\`），双击运行
2. 首次启动会自动创建 `GameDataKeeper/` 目录结构
3. **Steam 标签页** → 登录 Steam，安装游戏
4. 点击 **备份Steam凭证**（此后 Steam 免扫码登录，每次登录后需更新一次凭证）
5. 启动游戏 → 切回工具 → 点击 **添加游戏** 自动发现存档目录
6. 点击 **备份存档**

### 日常使用

```
登录云电脑 → 双击 GameDataKeeper.exe → 恢复Steam凭证 → 恢复存档 → 开玩
                                                              ↓
                      备份存档 ← 游戏结束 ←──────────────────┘
```

## 功能

| 功能 | 说明 |
|------|------|
| Steam 凭证备份 | 备份 SSFN + loginusers.vdf + config.vdf + 注册表，支持一键恢复并自动启动 Steam |
| 多游戏管理 | 支持配置多款游戏，每款游戏可管理多个存档路径 |
| 存档发现 | 启动游戏后从进程反查存档目录（psutil → WMIC → PowerShell 三级降级检测） |
| 手动配置 | 检测失败时可手动输入存档路径，支持查看当前进程列表辅助排查 |
| 存档备份 | ZIP 压缩备份，保留最近 5 份（FIFO 轮转），支持进度条实时显示 |
| 存档恢复 | 默认恢复最新备份，支持从历史存档中选择任意版本恢复 |
| 存档管理 | 支持打开存档目录、打开备份目录、删除游戏配置等操作 |

## 界面布局

- **Tab 栏**：Steam / 原神 / 崩坏:星穹铁道（后两者为预留扩展页）
- **系统状态区**：显示存档目录连接状态、Steam 安装路径、已配置游戏数量
- **已配置的游戏列表**：展示游戏名、存档类型、备份数、最近备份时间、备份总大小
- **快捷操作区**：备份存档 / 恢复存档 / 备份Steam凭证 / 恢复Steam凭证
- **历史存档区**：展示选中游戏的备份历史，支持选择特定版本恢复

## 项目结构

```
GameDateKepper/
├── main.py                         # tkinter 入口
├── requirements.txt
├── .github/workflows/build.yml     # GitHub Actions 自动编译 + Release 发布
├── shared/                         # 跨领域共享层
│   ├── backup.py                   # 通用 ZIP 压缩备份 + FIFO 轮转
│   ├── disk.py                     # 数据盘目录结构管理
│   ├── config_manager.py           # games.json 读写（多游戏配置）
│   ├── exceptions.py               # 统一异常层次结构
│   └── error_handler.py            # 错误日志 + 用户提示装饰器
├── app/                            # 应用壳（Tab 无关）
│   ├── main_window.py              # 主窗口 + Tab 栏 + 异步任务调度
│   ├── status_bar.py               # 状态栏组件
│   └── tab_registry.py             # Tab 注册中心（新增游戏只需注册一行）
├── games/                          # 每个游戏/平台一个独立模块
│   ├── _base/                      # 基类 + 模板
│   │   ├── base_tab.py             # Tab UI 基类（通用面板/列表/操作栏/历史）
│   │   ├── base_core.py            # Core 逻辑基类（通用备份/恢复/检测）
│   │   └── template/               # 新游戏脚手架（复制即用）
│   ├── steam/                      # Steam 模块
│   │   ├── ui/tab.py               # Steam Tab（继承 BaseGameTab）
│   │   └── core/                   # Steam 专属逻辑
│   │       ├── credential.py       # SSFN + VDF + 注册表
│   │       └── discovery.py        # 进程检测（psutil → WMIC → PowerShell）
│   ├── genshin/                    # 原神模块
│   │   ├── ui/tab.py
│   │   └── core/manager.py
│   └── hsr/                        # 崩坏:星穹铁道模块
│       ├── ui/tab.py
│       └── core/manager.py
└── config/
    └── games.json                  # 游戏配置（示例）
```

### 新增游戏

复制 `games/_base/template/` 目录，修改 3 处即可：

1. 类名 + `GAME_NAME` / `GAME_ID`
2. `SUPPORT_*` 标志位（是否支持凭证/发现/平台）
3. Core 层钩子方法（`detect_running` / `backup_credential` / `restore_credential`）

最后在 `games/__init__.py` 添加一行 `import` 即可自动注册到 Tab 栏。

## 开发

### 本地运行

```bash
pip install psutil
python main.py
```

### 编译 EXE

```bash
pip install psutil pyinstaller
pyinstaller --onefile --windowed --hidden-import psutil --name GameDataKeeper main.py
# 输出: dist/GameDataKeeper.exe
```

或直接推送代码到仓库，GitHub Actions 自动编译并发布到 Release。

### games.json 格式

```json
{
  "version": "1.3",
  "games": [
    {
      "id": "the_scroll_of_taiwu",
      "name": "The Scroll Of Taiwu",
      "steam_appid": "",
      "max_backups": 5,
      "save_paths": [
        {
          "name": "SaveGames",
          "path": "Z:\\steam\\steamapps\\common\\The Scroll Of Taiwu\\SaveGames",
          "description": "自动发现于 2026-07-07 15:30:24"
        }
      ],
      "backup_dir": "The_Scroll_Of_Taiwu"
    }
  ]
}
```
