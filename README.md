# GameDataKeeper v1.3 — 云电脑游戏数据持久化助手

一键备份/恢复 Steam 登录凭证和游戏存档。**零配置**——启动游戏后脚本自动发现存档位置。

## 适用场景

- 租用云电脑玩 Steam 游戏，每次会话结束数据被清空
- Steam 每次都要重新扫码登录
- 游戏存档需要手动备份到持久数据盘

## 快速开始

### 第一次：初始化 + 发现存档

```
1. 把整个 winjioaben 文件夹放到数据盘，比如 Q:\winjioaben\
2. 双击 GameDataKeeper.bat
3. [9] 初始化数据盘 → 选择你的数据盘盘符
4. 安装并登录 Steam，安装游戏
5. [3] 备份 Steam 凭证 ← 以后 Steam 不用重新登录
6. 启动游戏
7. 切回脚本 → [D] 发现存档位置 ← 自动从进程定位存档
8. [5] 备份游戏存档
```

### 之后每次使用

```
登录云电脑 → 双击 GameDataKeeper.bat → [2] 恢复全部 → 开玩
                                                 ↓
                   [1] 备份全部 ← 游戏结束 ←──────┘
```

## 功能菜单

```
  [1] 备份全部      Steam 凭证 + 游戏存档
  [2] 恢复全部      Steam 凭证 + 最新存档
  [3] 仅备份 Steam 凭证
  [4] 仅恢复 Steam 凭证
  [5] 备份游戏存档  压缩为 zip，自动保留最近 5 份
  [6] 恢复最新存档  解压最新备份到游戏目录
  [7] 查看存档历史  列出所有备份的版本
  [8] 选择存档恢复  从历史备份中挑选恢复
  [D] 发现存档位置  首次使用：启动游戏后自动定位存档
  [9] 初始化数据盘  首次使用或更换盘符
  [0] 退出
```

## 工作原理

### 存档自动发现（一次性的）

启动游戏 → 脚本检测进程路径（`steamapps\common\...`）→ 搜索游戏目录下的保存文件夹（`SaveFiles`、`Save`、`Saves` 等）→ 写入配置。之后不再需要游戏运行即可备份恢复。

### Steam 凭证

备份 Steam 安装目录下的 `loginusers.vdf` + `config.vdf` 以及注册表项 `HKCU\Software\Valve\Steam`。恢复后 Steam 自动登录，无需扫码。

### 游戏存档

每次备份生成带时间戳的 `.zip` 文件，保留最近 5 份（可在 `games.json` 中调整 `max_backups`）。超出自动淘汰最旧的（FIFO）。

```
数据盘:\GameDataKeeper\
├── .datadisk_id               ← 标识文件
├── Steam\
│   ├── config\loginusers.vdf
│   ├── config\config.vdf
│   └── registry.reg
└── Saves\{游戏名}\
    └── {存档目录名}\
        ├── 2026-07-07_143000.zip  ← 最新
        ├── 2026-07-06_180000.zip
        ├── 2026-07-05_090000.zip
        ├── 2026-07-04_220000.zip
        └── 2026-07-03_120000.zip  ← 最旧，下次淘汰
```

## 注意事项

1. **恢复 Steam 前需关闭 Steam**，脚本会提示是否自动关闭
2. **数据盘必须已连接**，否则操作会被阻止
3. **首次 Steam 仍需手动登录**，之后备份凭证即可免登
4. 如果游戏更新改变了存档位置，重新运行一次 `[D]` 即可

## 添加其他游戏

脚本自动发现依赖 Steam 库路径和常见的存档文件夹命名。如果自动发现没找到，可以手动编辑 `config\games.json`：

```json
{
  "version": "1.3",
  "games": [
    {
      "id": "mygame",
      "name": "游戏名",
      "max_backups": 5,
      "save_paths": [
        {
          "name": "主存档",
          "path": "C:\\完整\\存档\\路径"
        }
      ],
      "backup_dir": "MyGame"
    }
  ]
}
```

## 项目结构

```
winjioaben/
├── GameDataKeeper.bat        ← 双击运行
├── README.md
├── diag.bat                  ← 诊断工具
├── config/
│   └── games.json            ← 游戏配置（[D] 自动填充）
├── scripts/
│   ├── core.ps1              ← 核心逻辑
│   └── steam.ps1             ← Steam 凭证处理
├── tests/
│   └── test-paths.ps1        ← 路径验证
└── docs/
    ├── requirements.md
    └── development-plan.md
```
