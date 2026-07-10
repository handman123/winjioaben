# ============================================================
# 路径验证脚本
# 用途：在云电脑上运行此脚本，验证各路径是否有效
# 运行方式：在 PowerShell 中执行 .\tests\test-paths.ps1
# ============================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  GameDataKeeper 路径验证工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 获取脚本根目录
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot

# -----------------------------------------------------------
# 1. 检查 Steam 安装路径
# -----------------------------------------------------------
Write-Host ">>> 1. Steam 安装路径检测" -ForegroundColor Yellow

. (Join-Path $ProjectRoot "scripts\steam.ps1")

$steamPath = Find-SteamPath
if ($steamPath) {
    Write-Host "  [FOUND] Steam 路径: $steamPath" -ForegroundColor Green
    Write-Host ""

    # 检查关键文件
    $checks = @(
        @{ Label="loginusers.vdf"; Path=(Join-Path $steamPath "config\loginusers.vdf") },
        @{ Label="config.vdf"; Path=(Join-Path $steamPath "config\config.vdf") },
        @{ Label="steam.exe"; Path=(Join-Path $steamPath "steam.exe") }
    )

    foreach ($check in $checks) {
        if (Test-Path $check.Path) {
            $size = (Get-Item $check.Path).Length
            Write-Host "  [OK] $($check.Label) ($size bytes)" -ForegroundColor Green
        }
        else {
            Write-Host "  [MISS] $($check.Label) — 文件不存在" -ForegroundColor Red
        }
    }
}
else {
    Write-Host "  [NOT FOUND] 未找到 Steam 安装路径" -ForegroundColor Red
}

# -----------------------------------------------------------
# 2. 检查注册表
# -----------------------------------------------------------
Write-Host ""
Write-Host ">>> 2. Steam 注册表检测" -ForegroundColor Yellow

try {
    $regPath = "HKCU:\Software\Valve\Steam"
    if (Test-Path $regPath) {
        $props = Get-ItemProperty -Path $regPath -ErrorAction Stop
        Write-Host "  [OK] 注册表项存在" -ForegroundColor Green

        if ($props.AutoLoginUser) {
            Write-Host "  AutoLoginUser = $($props.AutoLoginUser)" -ForegroundColor Cyan
        }
        else {
            Write-Host "  [NOTE] AutoLoginUser 未设置" -ForegroundColor Yellow
        }
        if ($props.RememberPassword) {
            Write-Host "  RememberPassword = $($props.RememberPassword)" -ForegroundColor Cyan
        }
        else {
            Write-Host "  [NOTE] RememberPassword 未设置" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "  [MISS] 注册表项不存在" -ForegroundColor Red
    }
}
catch {
    Write-Host "  [ERR] 读取注册表失败: $($_.Exception.Message)" -ForegroundColor Red
}

# -----------------------------------------------------------
# 3. 检查游戏存档路径
# -----------------------------------------------------------
Write-Host ""
Write-Host ">>> 3. 游戏存档路径检测" -ForegroundColor Yellow

$configPath = Join-Path $ProjectRoot "config\games.json"
if (Test-Path $configPath) {
    $config = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json

    foreach ($game in $config.games) {
        Write-Host ""
        Write-Host "--- $($game.name) (ID: $($game.id)) ---" -ForegroundColor Cyan

        # 检查 Steam 游戏安装路径
        if ($steamPath -and $game.steam_appid) {
            $gameInstallPath = Join-Path $steamPath "steamapps\common"
            Write-Host "  Steam 库路径: $gameInstallPath" -ForegroundColor Gray

            # 尝试找到游戏文件夹（模糊匹配）
            $possibleDirs = Get-ChildItem -Path $gameInstallPath -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "*Taiwu*" -or $_.Name -like "*Scroll*" }
            if ($possibleDirs) {
                foreach ($d in $possibleDirs) {
                    Write-Host "  [FOUND] 游戏目录: $($d.FullName)" -ForegroundColor Green
                    # 检查游戏目录下是否有 Save 目录
                    $gameSaveDir = Join-Path $d.FullName "Save"
                    if (Test-Path $gameSaveDir) {
                        Write-Host "    -> 内含 Save 目录" -ForegroundColor Cyan
                    }
                }
            }
            else {
                Write-Host "  [NOTE] 未在 Steam 库中找到游戏目录（可能未安装或使用了其他库文件夹）" -ForegroundColor Yellow
            }
        }

        # 检查配置的存档路径
        foreach ($sp in $game.save_paths) {
            $resolved = [Environment]::ExpandEnvironmentVariables($sp.path)
            Write-Host "  检查: $($sp.name)" -ForegroundColor Gray
            Write-Host "    路径: $resolved" -ForegroundColor Gray

            if (Test-Path $resolved) {
                $itemCount = (Get-ChildItem -Path $resolved -Recurse -File -ErrorAction SilentlyContinue).Count
                $dirCount = (Get-ChildItem -Path $resolved -Directory -ErrorAction SilentlyContinue).Count
                Write-Host "    [EXISTS] 存在: $itemCount 个文件, $dirCount 个子目录" -ForegroundColor Green
            }
            else {
                # 检查父目录是否存在
                $parent = Split-Path -Parent $resolved
                if (Test-Path $parent) {
                    Write-Host "    [PARTIAL] 父目录存在但存档目录不存在" -ForegroundColor Yellow
                    Write-Host "      父目录: $parent" -ForegroundColor Gray
                    Write-Host "      父目录内容:" -ForegroundColor Gray
                    Get-ChildItem -Path $parent -ErrorAction SilentlyContinue | ForEach-Object {
                        Write-Host "        $($_.Name)" -ForegroundColor Gray
                    }
                }
                else {
                    Write-Host "    [MISS] 路径不存在" -ForegroundColor Red
                }
            }
        }
    }
}
else {
    Write-Host "  [ERR] 配置文件不存在: $configPath" -ForegroundColor Red
}

# -----------------------------------------------------------
# 4. 检查可用盘符
# -----------------------------------------------------------
Write-Host ""
Write-Host ">>> 4. 可用盘符检测" -ForegroundColor Yellow

$drives = Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -ne $null }
foreach ($drive in $drives) {
    $driveLetter = "$($drive.Name):"
    $freeGB = [math]::Round($drive.Free / 1GB, 2)
    $usedGB = [math]::Round(($drive.Used) / 1GB, 2)
    $totalGB = [math]::Round(($drive.Used + $drive.Free) / 1GB, 2)

    Write-Host "  $driveLetter  可用: ${freeGB}GB / 总计: ${totalGB}GB" -ForegroundColor Gray
}

# -----------------------------------------------------------
# 5. 环境变量
# -----------------------------------------------------------
Write-Host ""
Write-Host ">>> 5. 关键环境变量" -ForegroundColor Yellow

$envVars = @(
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "TEMP",
    "COMPUTERNAME",
    "USERNAME"
)

foreach ($var in $envVars) {
    $val = [Environment]::GetEnvironmentVariable($var)
    Write-Host "  %${var}% = $val" -ForegroundColor Gray
}

# -----------------------------------------------------------
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  验证完成！" -ForegroundColor Cyan
Write-Host "  请将以上输出复制给开发者，以确认路径配置" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "按回车键退出"
