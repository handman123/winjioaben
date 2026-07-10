# GameDataKeeper v2.0 - 云电脑游戏数据持久化助手

一键备份/恢复 Steam 登录凭证和游戏存档。启动游戏后自动发现存档位置，零配置。

## 适用场景

- 租用云电脑玩 Steam 游戏，每次会话结束数据被清空
- Steam 每次都要重新扫码登录
- 游戏存档需要手动备份到持久数据盘

## 快速开始

### 获取 exe

每次改完代码，`git push` 后去 GitHub → Actions → 最新运行 → Artifacts 下载 `GameDataKeeper-Windows.zip`，解压得到 `GameDataKeeper.exe`。

### 首次使用

```
1. 把 GameDataKeeper.exe 放到数据盘，比如 Q:\
2. 双击运行
3. Steam 标签页 → 登录 Steam，安装游戏
4. 点击 [备份Steam凭证]  ← 以后 Steam 不用重新登录
5. 启动游戏 → 切回工具 → 点击 [发现存档]
6. 点击 [备份存档]
```

### 日常使用

```
登录云电脑 → 双击 GameDataKeeper.exe → [恢复全部] → 开玩
                                              ↓
                      [备份全部] ← 游戏结束 ←──┘
```

## 界面布局

```
┌──────────────────────────────────────────────┐
│  [  Steam  ]   [  原神  ]   [  崩坏  ]        │  ← Tab 栏
├──────────────────────────────────────────────┤
│  系统状态: 数据盘 Q: ✓  Steam Z:\steam ✓      │
│  存档: Z:\...\SaveGames (存在)  [发现存档]    │
│                                              │
│  [备份全部] [恢复全部] [备份存档]              │
│  [备份Steam] [恢复Steam] [恢复存档]            │
│                                              │
│  存档历史:                                    │
│  ┌────────────────────────────────┐          │
│  │ 2026-07-08_003217.zip  328 MB  │          │
│  │ 2026-07-07_163645.zip  321 MB  │          │
│  └────────────────────────────────┘          │
├──────────────────────────────────────────────┤
│  就绪                              [进度条]   │
└──────────────────────────────────────────────┘
```

## 功能

| 功能 | 说明 |
|------|------|
| Steam 凭证备份 | 备份 SSFN + loginusers.vdf + config.vdf + 注册表 |
| Steam 凭证恢复 | 恢复后自动启动 Steam（免扫码） |
| 存档发现 | 启动游戏后从进程反查存档目录 |
| 存档备份 | zip 压缩，保留最近 5 份（FIFO 轮转） |
| 存档恢复 | 默认恢复最新，支持从历史选择 |
| 进度条 | 备份/恢复时实时显示进度 |

## 开发

### 项目结构

```
winjioaben/
├── main.py                    # Python 入口
├── build.bat                  # PyInstaller 打包
├── requirements.txt
├── GameDataKeeper.bat         # 本地运行入口（exe > python > CLI 降级）
├── .github/workflows/build.yml  # GitHub Actions 自动编译
├── core/                      # 业务逻辑层
│   ├── steam.py               # Steam 凭证（SSFN + 注册表）
│   ├── backup.py              # zip 压缩 + 轮转
│   ├── discovery.py           # 进程检测 + 存档发现
│   ├── disk.py                # 数据盘检测
│   └── config_manager.py      # games.json 读写
├── ui/                        # tkinter 界面层
│   ├── app.py                 # 主窗口 + Tab 栏
│   ├── steam_tab.py           # Steam 页
│   └── placeholder_tab.py     # 占位页
├── config/games.json
└── scripts/                   # PowerShell CLI（备选）
    ├── core.ps1
    └── steam.ps1
```

### 本地运行

```bash
pip install psutil
python main.py
```

### 编译 EXE

```bash
pip install psutil pyinstaller
pyinstaller --onefile --windowed --hidden-import psutil --name GameDataKeeper main.py
# 输出: dist\GameDataKeeper.exe
```

或直接推送代码，GitHub Actions 自动编译。
