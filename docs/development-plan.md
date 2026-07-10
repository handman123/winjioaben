# 开发文档：GameDataKeeper v1.3

## 1. 技术选型

| 组件 | 方案 | 原因 |
|------|------|------|
| 入口 | `.bat` 纯 ASCII | 双击运行，避免 cmd.exe GBK 编码问题 |
| 核心逻辑 | `.ps1` UTF-8 with BOM | PowerShell 5.1 通过 BOM 识别 UTF-8 |
| 存档压缩 | `Compress-Archive` / `Expand-Archive` | PowerShell 5.0+ 内置，无需第三方依赖 |
| 进程检测 | `Get-Process` + `MainModule.FileName` | 从进程路径反查 Steam 库中的游戏 |
| 数据盘识别 | 标识文件 `GameDataKeeper\.datadisk_id` | 扫描所有盘符查找标识文件 |

## 2. 项目结构

```
winjioaben/
├── GameDataKeeper.bat            # 纯 ASCII 入口，双击运行
├── README.md                     # 用户手册
├── diag.bat                      # 诊断工具（纯 ASCII）
├── config/
│   └── games.json                # 游戏配置，[D] 自动填充
├── scripts/
│   ├── core.ps1                  # 主菜单 + 数据盘检测 + 进程发现 + 备份/恢复
│   └── steam.ps1                 # Steam 凭证备份/恢复（dot-source 加载）
├── tests/
│   └── test-paths.ps1            # 路径验证工具
└── docs/
    ├── requirements.md
    └── development-plan.md
```

## 3. 核心模块

### 3.1 `steam.ps1` — Steam 凭证模块

| 函数 | 功能 |
|------|------|
| `Find-SteamPath` | 注册表查找 → 默认路径兜底 |
| `Test-SteamRunning` | 检测 steam.exe 是否在运行 |
| `Stop-SteamIfRunning` | 强制关闭 Steam 进程 |
| `Backup-SteamCredentials` | 复制 `loginusers.vdf` + `config.vdf`，导出注册表 |
| `Restore-SteamCredentials` | 恢复上述文件 + 导入注册表 |

通过 dot-source (`. "steam.ps1"`) 加载到 `core.ps1` 作用域中，所有函数直接可用。

### 3.2 `core.ps1` — 核心模块

#### 数据盘管理

| 函数 | 功能 |
|------|------|
| `Find-DataDisk` | 扫描所有盘符查找 `.datadisk_id` 标识文件 |
| `Initialize-DataDisk` | 创建目录结构 + 写入标识文件 |
| `Select-DataDiskInteractive` | 列出盘符让用户选择 |

#### 存档发现（一次性）

| 函数 | 功能 |
|------|------|
| `Discover-And-Save` | 检测运行中的 Steam 游戏进程 → 搜索 `SaveFiles/Save/Saves` 等目录 → 写入 `games.json` |

发现逻辑：
```
Get-Process → MainModule.FileName → 匹配 \steamapps\common\{游戏名}\
→ 提取游戏根目录 → Get-ChildItem -Recurse -Depth 4
→ 匹配 SaveFiles|Save|Saves|SaveData|Saved|SaveGames|saves|save
→ 有文件才算有效存档 → 写入 games.json
```

#### 存档备份/恢复

| 函数 | 功能 |
|------|------|
| `Backup-SavePath` | 压缩单个存档目录为 `.zip`，轮转保留最近 N 份 |
| `Restore-SavePath` | 解压指定 `.zip` 到目标位置（默认最新） |
| `Backup-GameSaves` | 遍历 `games.json` 所有游戏，调用 `Backup-SavePath` |
| `Restore-GameSaves` | 遍历 `games.json` 所有游戏，调用 `Restore-SavePath` |
| `List-BackupsForGame` | 列出所有备份的历史版本 |
| `Restore-GameSavesWithChoice` | 交互式选择特定备份恢复 |

#### 路径解析

| 函数 | 功能 |
|------|------|
| `Resolve-GamePath` | 展开环境变量（`%USERPROFILE%` 等）+ `%STEAM_PATH%` 占位符 |
| `Get-GameSavePaths` | 优先自动检测（`install_folder` + `relative_save_path`），兜底使用 `save_paths` |
| `Find-GameSavePath` | 扫描 Steam 库文件夹查找游戏存档（用于已配置游戏） |

#### UI

| 函数 | 功能 |
|------|------|
| `Show-Banner` | ASCII 艺术横幅 |
| `Show-Menu` | 主菜单渲染 |

### 3.3 `games.json` — 游戏配置

```json
{
  "version": "1.3",
  "games": [
    {
      "id": "taiwu",
      "name": "The Scroll Of Taiwu",
      "max_backups": 5,
      "save_paths": [
        {
          "name": "SaveFiles",
          "path": "C:\\...\\SaveFiles",
          "description": "自动发现于 2026-07-07 14:30:00"
        }
      ],
      "backup_dir": "The_Scroll_Of_Taiwu"
    }
  ]
}
```

字段说明：
- `max_backups`：保留的备份份数（默认 5）
- `save_paths[].path`：存档目录的绝对路径（由 `[D]` 自动填充）
- `backup_dir`：数据盘上的备份子目录名
- `install_folder` / `relative_save_path`：（可选）自动检测用的游戏目录名和相对存档路径
- `fallback_paths`：（可选）自动检测失败时的备选路径

## 4. 存档备份格式

```
每次备份生成: yyyy-MM-dd_HHmmss.zip
按文件名排序即为时间序（最新在前）

轮转规则: zip 数量 > max_backups → 删除最旧的
```

## 5. 编码兼容方案

| 文件类型 | 读取方 | 默认编码 | 解决方案 |
|----------|--------|----------|----------|
| `.bat` | cmd.exe | GBK (CP936) | **纯 ASCII**，不含任何中文 |
| `.ps1` | PowerShell 5.1 | ANSI (GBK) | **UTF-8 with BOM**，PowerShell 识别 BOM 后切换 UTF-8 |
| `.json` | `Get-Content -Encoding UTF8` | 显式指定 | UTF-8 无 BOM 亦可正常工作 |

## 6. 错误处理

- 全局 `trap {}` 捕获所有未处理异常
- `Main` 调用包裹在 `try/catch` 中
- 每个操作函数返回 `$true/$false` 表示成败
- 菜单循环不因单次操作失败而退出

## 7. 后续迭代方向

- GUI 界面（WinForms / WPF）：`core.ps1` 核心函数已与 UI 分离，可直接复用
- 定时自动备份：监控游戏进程退出时自动触发
- 云同步：将备份上传到云存储
- 支持非 Steam 游戏
