# ============================================================
# GameDataKeeper - 核心脚本 v1.1
# 职责：主菜单、数据盘检测、游戏存档备份/恢复（zip压缩+轮转）
#
# 架构说明：
#   - 业务逻辑与 UI 分离，所有核心函数均不依赖 Write-Host 的具体格式
#   - 后续创建 GUI 时，可直接调用本脚本中的函数（替换 UI 层即可）
#   - Steam 相关函数由同目录下的 steam.ps1 提供（通过 dot-source 加载）
# ============================================================

param(
    [switch]$NonInteractive,
    [string]$Action
)

# -----------------------------------------------------------
# 全局错误捕获——任何未处理的异常都会停在这里，不会闪退
# -----------------------------------------------------------
$Script:ErrorLog = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\error.log"
trap {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  脚本发生严重错误" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "错误信息: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "错误位置: $($_.InvocationInfo.PositionMessage)" -ForegroundColor Yellow
    Write-Host "调用堆栈:" -ForegroundColor Yellow
    Write-Host $_.ScriptStackTrace -ForegroundColor Gray
    Write-Host ""
    try { $_.Exception | Out-File $Script:ErrorLog -Append -Width 200 } catch {}
    Write-Host "详细错误已写入: $Script:ErrorLog" -ForegroundColor Gray
    Write-Host ""
    Read-Host "按回车键退出"
    exit 1
}

# -----------------------------------------------------------
# 初始化：定位脚本目录，加载依赖模块
# -----------------------------------------------------------
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot

# 加载 Steam 凭证模块
. (Join-Path $ScriptRoot "steam.ps1")

# 加载游戏配置文件
$GameConfigPath = Join-Path $ProjectRoot "config\games.json"
$Global:GamesConfig = $null

function Load-GameConfig {
    if (-not (Test-Path $GameConfigPath)) {
        Write-Error "找不到游戏配置文件: $GameConfigPath"
        return $false
    }
    try {
        $raw = Get-Content -Path $GameConfigPath -Raw -Encoding UTF8
        $Global:GamesConfig = $raw | ConvertFrom-Json
        return $true
    }
    catch {
        Write-Error "游戏配置文件解析失败: $($_.Exception.Message)"
        return $false
    }
}

# -----------------------------------------------------------
# 数据盘检测与识别
# -----------------------------------------------------------
$DataDiskIdentifier = "GameDataKeeper\.datadisk_id"

function Get-AvailableDrives {
    return (Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -ne $null } | ForEach-Object { "$($_.Name):" })
}

function Find-DataDisk {
    $drives = Get-AvailableDrives
    foreach ($drive in $drives) {
        $idFile = Join-Path $drive $DataDiskIdentifier
        if (Test-Path $idFile) {
            Write-Verbose "在 $drive 找到数据盘标识文件"
            return $drive
        }
    }
    return $null
}

function Test-DataDisk {
    param([string]$DriveLetter)
    $root = Join-Path $DriveLetter "GameDataKeeper"
    return (Test-Path $root)
}

function Initialize-DataDisk {
    param([string]$DriveLetter)

    Write-Host ""
    Write-Host "========== 初始化数据盘 $DriveLetter ==========" -ForegroundColor Cyan

    $root = Join-Path $DriveLetter "GameDataKeeper"

    $dirs = @(
        $root,
        (Join-Path $root "Steam\config"),
        (Join-Path $root "Saves")
    )
    foreach ($dir in $dirs) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Host "  创建目录: $dir" -ForegroundColor Gray
        }
    }

    # 写入标识文件
    $idFile = Join-Path $root ".datadisk_id"
    $idContent = @"
# GameDataKeeper 数据盘标识文件
# 创建时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
# 请勿删除此文件，否则脚本将无法识别数据盘
"@
    Set-Content -Path $idFile -Value $idContent -Encoding UTF8

    Write-Host ""
    Write-Host "数据盘初始化完成！" -ForegroundColor Green

    if ($Global:GamesConfig -and $Global:GamesConfig.games) {
        foreach ($game in $Global:GamesConfig.games) {
            $maxBackups = if ($game.max_backups) { $game.max_backups } else { 5 }
            foreach ($savePath in $game.save_paths) {
                $gameBackupDir = Join-Path $root "Saves\$($game.backup_dir)\$($savePath.name)"
                if (-not (Test-Path $gameBackupDir)) {
                    New-Item -ItemType Directory -Path $gameBackupDir -Force | Out-Null
                    Write-Host "  创建备份目录: $($game.name) / $($savePath.name) (保留 $maxBackups 份)" -ForegroundColor Gray
                }
            }
        }
    }

    return $true
}

function Select-DataDiskInteractive {
    $drives = Get-AvailableDrives
    if ($drives.Count -eq 0) {
        Write-Error "未检测到任何可用盘符"
        return $null
    }

    Write-Host ""
    Write-Host "可用盘符列表:" -ForegroundColor Yellow
    for ($i = 0; $i -lt $drives.Count; $i++) {
        Write-Host "  [$($i+1)] $($drives[$i])"
    }

    $choice = Read-Host "请选择数据盘 (输入序号)"
    try {
        $idx = [int]$choice - 1
        if ($idx -ge 0 -and $idx -lt $drives.Count) {
            return $drives[$idx]
        }
    }
    catch {}

    Write-Warning "无效选择"
    return $null
}

# -----------------------------------------------------------
# 存档压缩备份 / 轮转 / 恢复
# -----------------------------------------------------------

# -----------------------------------------------------------
# 存档路径自动检测与解析
# -----------------------------------------------------------

# 解析路径中的环境变量 + %STEAM_PATH% 占位符
function Resolve-GamePath {
    param([string]$RawPath)
    $resolved = [Environment]::ExpandEnvironmentVariables($RawPath)
    # 支持 %STEAM_PATH% 占位符（在 steam.ps1 找不到 Steam 时也能兜底）
    if ($resolved -match '%STEAM_PATH%') {
        $sp = Find-SteamPath
        if ($sp) { $resolved = $resolved -replace '%STEAM_PATH%', $sp }
    }
    return $resolved
}

# 扫描 Steam 所有库文件夹，自动查找游戏存档路径
# 返回：找到的存档完整路径，未找到则返回 $null
function Find-GameSavePath {
    param(
        [string]$SteamPath,
        [string]$InstallFolder,       # 游戏在 common 下的文件夹名，如 "The Scroll Of Taiwu"
        [string]$RelativeSavePath,    # 从游戏根目录到存档的相对路径，如 "The Scroll Of Taiwu\AlphaV1.0_Data\SaveFiles"
        [string[]]$FallbackPaths      # 兜底：硬编码的备选路径列表
    )

    # --- 策略1：扫描 Steam 库文件夹 ---
    if ($SteamPath -and $InstallFolder -and $RelativeSavePath) {
        $libraryFolders = @()

        # 默认库
        $defaultLib = Join-Path $SteamPath "steamapps"
        if (Test-Path $defaultLib) { $libraryFolders += $defaultLib }

        # 解析 libraryfolders.vdf 获取额外的库路径
        $vdfPath = Join-Path $SteamPath "steamapps\libraryfolders.vdf"
        if (Test-Path $vdfPath) {
            try {
                $vdfContent = Get-Content $vdfPath -Raw -ErrorAction SilentlyContinue
                # VDF 格式中路径行如: "path"  "D:\\SteamLibrary"
                $matches = [regex]::Matches($vdfContent, '"path"\s+"([^"]+)"')
                foreach ($m in $matches) {
                    $libPath = $m.Groups[1].Value -replace '\\\\', '\'
                    $libSteamApps = Join-Path $libPath "steamapps"
                    if (Test-Path $libSteamApps) {
                        $libraryFolders += $libSteamApps
                        Write-Verbose "发现 Steam 库: $libSteamApps"
                    }
                }
            }
            catch {
                Write-Verbose "解析 libraryfolders.vdf 失败: $_"
            }
        }

        # 在每个库文件夹中查找游戏
        foreach ($lib in $libraryFolders) {
            $gameRoot = Join-Path $lib "common\$InstallFolder"
            if (Test-Path $gameRoot) {
                $candidate = Join-Path $gameRoot $RelativeSavePath
                if (Test-Path $candidate) {
                    Write-Host "  [自动检测] 找到存档: $candidate" -ForegroundColor Cyan
                    return $candidate
                }
                else {
                    Write-Verbose "游戏目录存在 ($gameRoot) 但存档路径不存在: $candidate"
                }
            }
        }
    }

    # --- 策略2：尝试兜底硬编码路径 ---
    if ($FallbackPaths) {
        foreach ($fb in $FallbackPaths) {
            $resolved = [Environment]::ExpandEnvironmentVariables($fb)
            if (Test-Path $resolved) {
                Write-Host "  [备选路径] 找到存档: $resolved" -ForegroundColor DarkYellow
                return $resolved
            }
        }
    }

    return $null
}

# 获取游戏的存档路径（优先自动检测，兜底配置路径）
function Get-GameSavePaths {
    param(
        [Parameter(Mandatory=$true)]$Game,
        [string]$SteamPath,
        [switch]$ForRestore   # 恢复模式：允许目录尚不存在（恢复时会自动创建）
    )

    $foundPaths = @()

    # 如果配置了自动检测，优先尝试
    if ($Game.install_folder -and $Game.relative_save_path) {
        $autoPath = Find-GameSavePath `
            -SteamPath $SteamPath `
            -InstallFolder $Game.install_folder `
            -RelativeSavePath $Game.relative_save_path `
            -FallbackPaths $Game.fallback_paths

        if ($autoPath) {
            $foundPaths += @{ Name = "自动检测"; Path = $autoPath }
        }
    }

    # 如果自动检测没找到，尝试配置中的手动路径
    if ($foundPaths.Count -eq 0 -and $Game.save_paths) {
        foreach ($sp in $Game.save_paths) {
            $resolved = Resolve-GamePath $sp.path
            # 备份时要求路径存在；恢复时不要求（目录可能还没创建）
            if ($ForRestore -or (Test-Path $resolved)) {
                $extra = if ($ForRestore -and -not (Test-Path $resolved)) { " (目录尚不存在，恢复时自动创建)" } else { "" }
                Write-Host "  [配置路径] $($sp.name): $resolved$extra" -ForegroundColor DarkYellow
                $foundPaths += @{ Name = $sp.name; Path = $resolved }
            }
        }
    }

    # 如果所有路径都找不到，列出配置路径供排查
    if ($foundPaths.Count -eq 0) {
        Write-Host "  [WARN] 未找到存档目录，已尝试:" -ForegroundColor Yellow
        if ($Game.install_folder) {
            Write-Host "    自动检测: Steam库/common/$($Game.install_folder)/$($Game.relative_save_path)" -ForegroundColor Gray
        }
        if ($Game.fallback_paths) {
            foreach ($fb in $Game.fallback_paths) {
                Write-Host "    备选: $fb" -ForegroundColor Gray
            }
        }
        if ($Game.save_paths) {
            foreach ($sp in $Game.save_paths) {
                Write-Host "    配置: $($sp.path)" -ForegroundColor Gray
            }
        }
    }

    return $foundPaths
}

# 备份单个存档路径：压缩为 zip，轮转保留最近 N 份
function Backup-SavePath {
    param(
        [Parameter(Mandatory=$true)][string]$SourcePath,
        [Parameter(Mandatory=$true)][string]$BackupBaseDir,
        [string]$Label = "存档",
        [int]$MaxBackups = 5
    )

    if (-not (Test-Path $SourcePath)) {
        Write-Host "  [SKIP] 源目录不存在: $SourcePath" -ForegroundColor Yellow
        return $false
    }

    # 检查源目录是否有内容
    $sourceItems = @(Get-ChildItem -Path $SourcePath -ErrorAction SilentlyContinue)
    if ($sourceItems.Count -eq 0) {
        Write-Host "  [SKIP] 源目录为空: $SourcePath" -ForegroundColor Yellow
        return $false
    }

    # 确保备份目录存在
    if (-not (Test-Path $BackupBaseDir)) {
        New-Item -ItemType Directory -Path $BackupBaseDir -Force | Out-Null
    }

    # 生成时间戳文件名（按字符串排序即为时间序）
    $timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
    $zipName = "$timestamp.zip"
    $zipPath = Join-Path $BackupBaseDir $zipName

    $rawSize = [math]::Round((
        Get-ChildItem -Path $SourcePath -Recurse -File -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum
    ).Sum / 1KB, 1)
    Write-Host "  压缩 $Label → $zipName" -ForegroundColor Gray
    Write-Host "    源  : $SourcePath ($rawSize KB)" -ForegroundColor Gray

    $files = @(Get-ChildItem -Path $SourcePath -Recurse -File -ErrorAction SilentlyContinue)
    $totalBytes = ($files | Measure-Object -Property Length -Sum).Sum
    if ($totalBytes -eq 0) {
        Write-Host "  [SKIP] 源目录无文件" -ForegroundColor Yellow
        return $false
    }
    $totalMB = [math]::Round($totalBytes / 1MB, 1)

    Write-Host "  压缩 $Label → $zipName  ($totalMB MB)" -ForegroundColor Gray

    # 检测 .NET 压缩 API 是否可用，不可用则降级到 Compress-Archive（无进度条）
    $hasZipApi = $false
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction Stop
        $null = [System.IO.Compression.ZipFile]
        $null = [System.IO.Compression.ZipArchiveMode]
        $hasZipApi = $true
    } catch {}

    if ($hasZipApi) {
        # 逐文件压缩 + 进度条
        $archive = $null
        $bytesDone = 0L
        $barWidth = 28

        try {
            $archive = [System.IO.Compression.ZipFile]::Open($zipPath, [System.IO.Compression.ZipArchiveMode]::Create)

            foreach ($file in $files) {
                $entryName = $file.FullName.Substring($SourcePath.Length).TrimStart('\', '/')
                if ($entryName -eq '') { $entryName = $file.Name }

                $entry = $archive.CreateEntry($entryName, [System.IO.Compression.CompressionLevel]::Optimal)
                $fs = $es = $null
                try {
                    $fs = [System.IO.File]::OpenRead($file.FullName)
                    $es = $entry.Open()
                    $fs.CopyTo($es)
                    $bytesDone += $file.Length

                    $pct = [math]::Min(100, [math]::Round($bytesDone * 100 / $totalBytes))
                    $filled = [math]::Round($pct * $barWidth / 100)
                    $bar = '[' + ('=' * $filled) + '>' + (' ' * ($barWidth - $filled)) + ']'
                    $doneMB = [math]::Round($bytesDone / 1MB, 1)
                    Write-Host ("`r  压缩中  $bar $pct%  ${doneMB}MB/$totalMB MB") -NoNewline
                }
                finally {
                    if ($fs) { $fs.Dispose() }
                    if ($es) { $es.Dispose() }
                }
            }

            Write-Host ""
            $archive.Dispose()
            $archive = $null

            $zipSize = [math]::Round((Get-Item $zipPath).Length / 1KB, 1)
            Write-Host "  [OK] 备份完成: $zipName ($zipSize KB)" -ForegroundColor Green
        }
        catch {
            if ($archive) { try { $archive.Dispose() } catch {} }
            Write-Host ""
            Write-Host "  [FAIL] 压缩失败: $($_.Exception.Message)" -ForegroundColor Red
            return $false
        }
    }
    else {
        # 降级：使用 Compress-Archive（无进度条，但功能完整）
        Write-Host "  使用内置 Compress-Archive（无进度条）..." -ForegroundColor Gray
        try {
            Compress-Archive -Path "$SourcePath\*" -DestinationPath $zipPath -Force -ErrorAction Stop
            if (-not (Test-Path $zipPath)) {
                Write-Host "  [FAIL] 压缩文件未生成" -ForegroundColor Red
                return $false
            }
            $zipSize = [math]::Round((Get-Item $zipPath).Length / 1KB, 1)
            Write-Host "  [OK] 备份完成: $zipName ($zipSize KB)" -ForegroundColor Green
        }
        catch {
            Write-Host "  [FAIL] 压缩失败: $($_.Exception.Message)" -ForegroundColor Red
            return $false
        }
    }

    # 轮转：保留最近 MaxBackups 个，删除多余的旧备份（FIFO）
    $existingZips = @(Get-ChildItem -Path $BackupBaseDir -Filter "*.zip" -File | Sort-Object Name -Descending)

    if ($existingZips.Count -gt $MaxBackups) {
        $toDelete = $existingZips | Select-Object -Skip $MaxBackups
        foreach ($old in $toDelete) {
            try {
                Remove-Item -Path $old.FullName -Force
                Write-Host "  [轮转] 已淘汰旧备份: $($old.Name)" -ForegroundColor DarkGray
            }
            catch {
                Write-Host "  [WARN] 无法删除旧备份: $($old.Name)" -ForegroundColor Yellow
            }
        }
    }

    Write-Host "  当前备份数: $([math]::Min($existingZips.Count, $MaxBackups)) / $MaxBackups" -ForegroundColor Gray
    return $true
}

# 恢复单个存档路径：解压指定 zip 到目标位置
function Restore-SavePath {
    param(
        [Parameter(Mandatory=$true)][string]$SavePath,
        [Parameter(Mandatory=$true)][string]$BackupBaseDir,
        [string]$Label = "存档",
        [string]$SpecificBackup = ""    # 空 = 最新
    )

    if (-not (Test-Path $BackupBaseDir)) {
        Write-Host "  [SKIP] 备份目录为空: $BackupBaseDir" -ForegroundColor Yellow
        return $false
    }

    $existingZips = @(Get-ChildItem -Path $BackupBaseDir -Filter "*.zip" -File | Sort-Object Name -Descending)

    if ($existingZips.Count -eq 0) {
        Write-Host "  [SKIP] 没有可用的备份" -ForegroundColor Yellow
        return $false
    }

    # 选择备份
    $zipToRestore = $null
    if ($SpecificBackup -ne "") {
        $zipToRestore = $existingZips | Where-Object { $_.Name -eq $SpecificBackup }
        if (-not $zipToRestore) {
            Write-Host "  [FAIL] 指定的备份不存在: $SpecificBackup" -ForegroundColor Red
            return $false
        }
    }
    else {
        $zipToRestore = $existingZips[0]  # 最新的
    }

    $zipSize = [math]::Round($zipToRestore.Length / 1KB, 1)
    Write-Host "  恢复 $Label ← $($zipToRestore.Name) ($zipSize KB)" -ForegroundColor Gray
    Write-Host "    目标: $SavePath" -ForegroundColor Gray

    # 确保目标目录的父级链完整存在
    $parent = Split-Path -Parent $SavePath
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
        Write-Host "    已创建父目录: $parent" -ForegroundColor Gray
    }

    # 清理目标目录
    if (Test-Path $SavePath) {
        try {
            Get-ChildItem -Path $SavePath -Recurse | Remove-Item -Recurse -Force -ErrorAction Stop
            Write-Host "    已清理旧存档" -ForegroundColor Gray
        }
        catch {
            Write-Host "  [WARN] 清理旧存档出错: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
    else {
        New-Item -ItemType Directory -Path $SavePath -Force | Out-Null
        Write-Host "    已创建存档目录" -ForegroundColor Gray
    }

    # 解压（逐文件，显示进度条）
    # 检测 .NET 压缩 API 是否可用
    $hasZipApi = $false
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction Stop
        $null = [System.IO.Compression.ZipFile]
        $null = [System.IO.Compression.ZipArchiveMode]
        $hasZipApi = $true
    } catch {}

    if ($hasZipApi) {
        $zipArchive = $null
        $bytesDone = 0L
        $barWidth = 28

        try {
            $zipArchive = [System.IO.Compression.ZipFile]::OpenRead($zipToRestore.FullName)
            $entries = @($zipArchive.Entries)
            $totalBytes = ($entries | Measure-Object -Property Length -Sum).Sum

            foreach ($entry in $entries) {
                $destPath = Join-Path $SavePath $entry.FullName
                if ($entry.FullName.EndsWith('/') -or $entry.FullName.EndsWith('\') -or $entry.Length -eq 0) {
                    if (-not (Test-Path $destPath)) {
                        New-Item -ItemType Directory -Path $destPath -Force | Out-Null
                    }
                    continue
                }
                $destParent = Split-Path -Parent $destPath
                if (-not (Test-Path $destParent)) {
                    New-Item -ItemType Directory -Path $destParent -Force | Out-Null
                }
                $fs = $null
                try {
                    $fs = [System.IO.File]::Create($destPath)
                    $entry.Open().CopyTo($fs)
                    $bytesDone += $entry.Length
                }
                finally {
                    if ($fs) { $fs.Dispose() }
                }

                if ($totalBytes -gt 0) {
                    $pct = [math]::Min(100, [math]::Round($bytesDone * 100 / $totalBytes))
                    $filled = [math]::Round($pct * $barWidth / 100)
                    $bar = '[' + ('=' * $filled) + '>' + (' ' * ($barWidth - $filled)) + ']'
                    $doneMB = [math]::Round($bytesDone / 1MB, 1)
                    $totalMB = [math]::Round($totalBytes / 1MB, 1)
                    Write-Host ("`r  解压中  $bar $pct%  ${doneMB}MB/$totalMB MB") -NoNewline
                }
            }

            Write-Host ""
            $zipArchive.Dispose()
            $zipArchive = $null
            Write-Host "  [OK] 恢复完成: $($zipToRestore.Name)" -ForegroundColor Green
            return $true
        }
        catch {
            if ($zipArchive) { try { $zipArchive.Dispose() } catch {} }
            Write-Host ""
            Write-Host "  [FAIL] 解压失败: $($_.Exception.Message)" -ForegroundColor Red
            return $false
        }
    }
    else {
        # 降级：使用 Expand-Archive（无进度条）
        Write-Host "  使用内置 Expand-Archive（无进度条）..." -ForegroundColor Gray
        try {
            Expand-Archive -Path $zipToRestore.FullName -DestinationPath $SavePath -Force -ErrorAction Stop
            Write-Host "  [OK] 恢复完成: $($zipToRestore.Name)" -ForegroundColor Green
            return $true
        }
        catch {
            Write-Host "  [FAIL] 解压失败: $($_.Exception.Message)" -ForegroundColor Red
            return $false
        }
    }
}

# 列出所有备份供用户选择
function List-BackupsForGame {
    param(
        [Parameter(Mandatory=$true)][string]$DataDrive
    )

    Write-Host ""
    Write-Host "========== 存档历史 ==========" -ForegroundColor Cyan

    if (-not $Global:GamesConfig -or -not $Global:GamesConfig.games) {
        Write-Warning "游戏配置为空"
        return
    }

    $saveRoot = Join-Path $DataDrive "GameDataKeeper\Saves"
    $steamPath = Find-SteamPath

    foreach ($game in $Global:GamesConfig.games) {
        Write-Host ""
        Write-Host "--- $($game.name) ---" -ForegroundColor Yellow

        $foundPaths = Get-GameSavePaths -Game $game -SteamPath $steamPath -ForRestore

        foreach ($fp in $foundPaths) {
            $backupDir = Join-Path $saveRoot "$($game.backup_dir)\$($fp.Name)"

            if (-not (Test-Path $backupDir)) {
                Write-Host "  [$($fp.Name)] 暂无备份" -ForegroundColor DarkGray
                continue
            }

            $zips = @(Get-ChildItem -Path $backupDir -Filter "*.zip" -File | Sort-Object Name -Descending)
            if ($zips.Count -eq 0) {
                Write-Host "  [$($fp.Name)] 暂无备份" -ForegroundColor DarkGray
                continue
            }

            Write-Host "  [$($fp.Name)] 共 $($zips.Count) 份备份:" -ForegroundColor White
            for ($i = 0; $i -lt $zips.Count; $i++) {
                $sizeKB = [math]::Round($zips[$i].Length / 1KB, 1)
                $time = $zips[$i].LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
                $marker = if ($i -eq 0) { " ← 最新" } else { "" }
                Write-Host "    [$($i+1)] $($zips[$i].Name)  |  $sizeKB KB  |  $time$marker" -ForegroundColor $(if ($i -eq 0) { "Green" } else { "Gray" })
            }
        }
    }
}

# 交互式选择并恢复指定存档
function Restore-GameSavesWithChoice {
    param([string]$DataDrive)

    Write-Host ""
    Write-Host "========== 选择存档恢复 ==========" -ForegroundColor Cyan

    if (-not $Global:GamesConfig -or -not $Global:GamesConfig.games) {
        Write-Warning "游戏配置为空"
        return
    }

    $saveRoot = Join-Path $DataDrive "GameDataKeeper\Saves"
    $steamPath = Find-SteamPath

    foreach ($game in $Global:GamesConfig.games) {
        Write-Host ""
        Write-Host "--- $($game.name) ---" -ForegroundColor Yellow

        $foundPaths = Get-GameSavePaths -Game $game -SteamPath $steamPath -ForRestore

        foreach ($fp in $foundPaths) {
            $backupDir = Join-Path $saveRoot "$($game.backup_dir)\$($fp.Name)"

            if (-not (Test-Path $backupDir)) {
                Write-Host "  [$($fp.Name)] 暂无备份，跳过" -ForegroundColor DarkGray
                continue
            }

            $zips = @(Get-ChildItem -Path $backupDir -Filter "*.zip" -File | Sort-Object Name -Descending)
            if ($zips.Count -eq 0) {
                Write-Host "  [$($fp.Name)] 暂无备份，跳过" -ForegroundColor DarkGray
                continue
            }

            Write-Host ""
            Write-Host "  $($fp.Name) — $($zips.Count) 份备份可用:" -ForegroundColor White
            for ($i = 0; $i -lt $zips.Count; $i++) {
                $sizeKB = [math]::Round($zips[$i].Length / 1KB, 1)
                $time = $zips[$i].LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
                $prefix = if ($i -eq 0) { "→" } else { " " }
                Write-Host "  $prefix [$($i+1)] $($zips[$i].Name)  ($sizeKB KB, $time)" -ForegroundColor $(if ($i -eq 0) { "Green" } else { "Gray" })
            }

            Write-Host ""
            $choice = Read-Host "  恢复哪一份? (1=$($zips.Count), 回车=最新, 0=跳过)"

            if ($choice -eq '0') {
                Write-Host "  已跳过" -ForegroundColor Gray
                continue
            }
            if ($choice -eq '') {
                $choice = '1'
            }

            try {
                $idx = [int]$choice - 1
                if ($idx -ge 0 -and $idx -lt $zips.Count) {
                    $selectedZip = $zips[$idx].Name
                    Restore-SavePath -SavePath $fp.Path -BackupBaseDir $backupDir -Label $fp.Name -SpecificBackup $selectedZip
                }
                else {
                    Write-Host "  无效序号" -ForegroundColor Red
                }
            }
            catch {
                Write-Host "  输入无效" -ForegroundColor Red
            }
        }
    }

    Write-Host ""
    Write-Host "存档恢复完成！" -ForegroundColor Green
}

# -----------------------------------------------------------
# 一次性存档发现：启动游戏 → 脚本从进程定位存档 → 写入配置
# 只需执行一次，之后正常备份/恢复即可
# -----------------------------------------------------------

function Discover-And-Save {
    param([string]$DataDrive)

    Write-Host ""
    Write-Host "========== 发现存档位置（首次设置） ==========" -ForegroundColor Cyan
    Write-Host "请确保游戏正在运行，脚本将自动定位存档目录" -ForegroundColor Gray
    Write-Host ""

    # 1. 从进程找到游戏
    $game = $null
    $procs = Get-Process -ErrorAction SilentlyContinue
    foreach ($p in $procs) {
        try { $exe = $p.MainModule.FileName } catch { continue }
        if ($exe -match '\\steamapps\\common\\([^\\]+)') {
            $folderName = $Matches[1]
            if ($exe -match '^(.+?\\steamapps\\common\\[^\\]+)') {
                $gameRoot = $Matches[1]
                $game = @{ Folder = $folderName; Root = $gameRoot }
                Write-Host "检测到游戏: $folderName" -ForegroundColor Green
                Write-Host "安装位置: $gameRoot" -ForegroundColor Gray
                break
            }
        }
    }
    if (-not $game) {
        Write-Host "未检测到正在运行的 Steam 游戏" -ForegroundColor Yellow
        Write-Host "请先启动游戏，再运行此功能" -ForegroundColor Gray
        Read-Host "按回车键返回"
        return
    }

    # 2. 搜索存档目录
    Write-Host ""
    Write-Host "正在搜索存档目录..." -ForegroundColor Gray
    $saveDirs = @()
    Get-ChildItem $game.Root -Directory -Recurse -Depth 4 -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_.Name -match '^(SaveFiles|Save|Saves|SaveData|Saved|SaveGames|saves|save)$') {
            $fc = @(Get-ChildItem $_.FullName -File -Recurse -ErrorAction SilentlyContinue).Count
            if ($fc -gt 0) {
                $saveDirs += @{ name = $_.Name; path = $_.FullName; files = $fc }
                Write-Host "  发现: $($_.Name) ($fc 个文件)" -ForegroundColor Cyan
                Write-Host "        $($_.FullName)" -ForegroundColor DarkGray
            }
        }
    }

    if ($saveDirs.Count -eq 0) {
        Write-Host "未自动发现存档目录" -ForegroundColor Yellow
        Write-Host "请手动输入存档路径，例如：" -ForegroundColor Gray
        Write-Host "  $($game.Root)\The Scroll Of Taiwu\AlphaV1.0_Data\SaveFiles" -ForegroundColor DarkGray
        $manual = Read-Host "路径 (回车=取消)"
        if ($manual -ne '' -and (Test-Path $manual)) {
            $saveDirs += @{ name = "手动指定"; path = $manual; files = 1 }
        }
        else {
            Read-Host "按回车键返回"
            return
        }
    }

    # 3. 写入 games.json
    $safeName = $game.Folder -replace '[\\/:*?"<>| ]', '_'
    $savePaths = @()
    foreach ($s in $saveDirs) {
        $savePaths += @{
            name = $s.name
            path = $s.path
            description = "自动发现于 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        }
    }

    $newConfig = @{
        version = "1.3"
        comment = "存档路径由脚本自动发现，可手动修改"
        games = @(@{
            id = $safeName.ToLower()
            name = $game.Folder
            steam_appid = ""
            max_backups = 5
            save_paths = $savePaths
            backup_dir = $safeName
        })
    }

    $configPath = Join-Path $ProjectRoot "config\games.json"
    $newConfig | ConvertTo-Json -Depth 5 | Set-Content -Path $configPath -Encoding UTF8
    $Global:GamesConfig = $newConfig

    # 同时创建数据盘备份目录
    $backupBase = Join-Path $DataDrive "GameDataKeeper\Saves\$safeName"
    foreach ($s in $saveDirs) {
        $d = Join-Path $backupBase $s.name
        if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
        Write-Host "  备份目录: $d" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  发现完成！存档配置已保存" -ForegroundColor Green
    Write-Host "  游戏: $($game.Folder)" -ForegroundColor White
    Write-Host "  存档: $($saveDirs.Count) 个目录" -ForegroundColor White
    Write-Host "  之后选择 [5] 备份 / [6] 恢复即可" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Green
}

# -----------------------------------------------------------
# 游戏存档备份 / 恢复（遍历 games.json）
# -----------------------------------------------------------

function Backup-GameSaves {
    param([string]$DataDrive)

    Write-Host ""
    Write-Host "========== 备份游戏存档 ==========" -ForegroundColor Cyan

    if (-not $Global:GamesConfig -or -not $Global:GamesConfig.games) {
        Write-Warning "游戏配置为空"
        return 0
    }

    $saveRoot = Join-Path $DataDrive "GameDataKeeper\Saves"
    $steamPath = Find-SteamPath
    $successCount = 0

    foreach ($game in $Global:GamesConfig.games) {
        Write-Host ""
        Write-Host "--- $($game.name) ---" -ForegroundColor Yellow

        $maxBackups = if ($game.max_backups) { $game.max_backups } else { 5 }
        $gameSaved = $false

        # 使用自动检测获取存档路径（备份要求路径存在）
        $foundPaths = Get-GameSavePaths -Game $game -SteamPath $steamPath

        foreach ($fp in $foundPaths) {
            $backupDir = Join-Path $saveRoot "$($game.backup_dir)\$($fp.Name)"

            if (Backup-SavePath -SourcePath $fp.Path -BackupBaseDir $backupDir -Label $fp.Name -MaxBackups $maxBackups) {
                $gameSaved = $true
            }
        }

        if ($gameSaved) { $successCount++ }
    }

    Write-Host ""
    Write-Host "备份完成: $successCount / $($Global:GamesConfig.games.Count) 款游戏" -ForegroundColor Green
    return $successCount
}

function Restore-GameSaves {
    param([string]$DataDrive)

    Write-Host ""
    Write-Host "========== 恢复最新存档 ==========" -ForegroundColor Cyan

    if (-not $Global:GamesConfig -or -not $Global:GamesConfig.games) {
        Write-Warning "游戏配置为空"
        return 0
    }

    $saveRoot = Join-Path $DataDrive "GameDataKeeper\Saves"
    $steamPath = Find-SteamPath
    $successCount = 0

    foreach ($game in $Global:GamesConfig.games) {
        Write-Host ""
        Write-Host "--- $($game.name) ---" -ForegroundColor Yellow

        # 使用自动检测获取存档路径
        $foundPaths = Get-GameSavePaths -Game $game -SteamPath $steamPath -ForRestore
        $gameRestored = $false

        foreach ($fp in $foundPaths) {
            $backupDir = Join-Path $saveRoot "$($game.backup_dir)\$($fp.Name)"

            if (Restore-SavePath -SavePath $fp.Path -BackupBaseDir $backupDir -Label $fp.Name) {
                $gameRestored = $true
            }
        }

        if ($gameRestored) { $successCount++ }
    }

    Write-Host ""
    Write-Host "恢复完成: $successCount / $($Global:GamesConfig.games.Count) 款游戏" -ForegroundColor Green
    return $successCount
}

# -----------------------------------------------------------
# 组合操作
# -----------------------------------------------------------

function Backup-All {
    param([string]$DataDrive, [string]$SteamPath)
    $null = Backup-SteamCredentials -SteamPath $SteamPath -DataDrive $DataDrive
    $null = Backup-GameSaves -DataDrive $DataDrive
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  全部操作完成" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
}

function Restore-All {
    param([string]$DataDrive, [string]$SteamPath)
    $null = Restore-SteamCredentials -SteamPath $SteamPath -DataDrive $DataDrive
    $null = Restore-GameSaves -DataDrive $DataDrive
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  全部操作完成" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
}

# -----------------------------------------------------------
# 欢迎横幅
# -----------------------------------------------------------
function Show-Banner {
    Write-Host ""
    Write-Host "  ╔══════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "  ║   GameDataKeeper v1.3                ║" -ForegroundColor Cyan
    Write-Host "  ║   云电脑游戏数据持久化助手            ║" -ForegroundColor Cyan
    Write-Host "  ╚══════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

# -----------------------------------------------------------
# 主菜单
# -----------------------------------------------------------
function Show-Menu {
    param([string]$DataDrive, [string]$SteamPath)

    if ($DataDrive) {
        Write-Host "  数据盘: $DataDrive (已连接)" -ForegroundColor Green
    }
    else {
        Write-Host "  数据盘: 未检测到" -ForegroundColor Red
    }

    if ($SteamPath) {
        Write-Host "  Steam : $SteamPath" -ForegroundColor Gray
    }
    else {
        Write-Host "  Steam : 未找到" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "  请选择操作:" -ForegroundColor White
    Write-Host "  ───────────────────────────────────" -ForegroundColor DarkGray
    Write-Host "  [1] 备份全部  (Steam凭证 + 游戏存档)" -ForegroundColor White
    Write-Host "  [2] 恢复全部  (Steam凭证 + 最新存档)" -ForegroundColor White
    Write-Host "  [3] 仅备份 Steam 凭证" -ForegroundColor White
    Write-Host "  [4] 仅恢复 Steam 凭证" -ForegroundColor White
    Write-Host "  [5] 备份游戏存档 (压缩+轮转)" -ForegroundColor White
    Write-Host "  [6] 恢复最新存档" -ForegroundColor White
    Write-Host "  ───────────────────────────────────" -ForegroundColor DarkGray
    Write-Host "  [7] 查看存档历史" -ForegroundColor Cyan
    Write-Host "  [8] 选择存档恢复 (从历史中挑选)" -ForegroundColor Cyan
    Write-Host "  ───────────────────────────────────" -ForegroundColor DarkGray
    Write-Host "  [D] 发现存档位置 (首次：启动游戏后运行)" -ForegroundColor Magenta
    Write-Host "  ───────────────────────────────────" -ForegroundColor DarkGray
    Write-Host "  [9] 首次初始化 / 重新设置数据盘" -ForegroundColor Yellow
    Write-Host "  [0] 退出" -ForegroundColor White
    Write-Host ""
}

# -----------------------------------------------------------
# 主入口
# -----------------------------------------------------------
function Main {
    if (-not (Load-GameConfig)) {
        Write-Host "按任意键退出..."
        Read-Host
        return
    }

    # 非交互模式
    if ($NonInteractive -and $Action) {
        $dataDrive = Find-DataDisk
        if (-not $dataDrive) { Write-Error "未找到数据盘"; exit 1 }
        $steamPath = Find-SteamPath
        if (-not $steamPath) { Write-Error "未找到 Steam"; exit 1 }
        switch ($Action) {
            "backup-all"    { Backup-All -DataDrive $dataDrive -SteamPath $steamPath }
            "restore-all"   { Restore-All -DataDrive $dataDrive -SteamPath $steamPath }
            "backup-steam"  { Backup-SteamCredentials -SteamPath $steamPath -DataDrive $dataDrive | Out-Null }
            "restore-steam" { Restore-SteamCredentials -SteamPath $steamPath -DataDrive $dataDrive | Out-Null }
            "backup-saves"  { Backup-GameSaves -DataDrive $dataDrive | Out-Null }
            "restore-saves" { Restore-GameSaves -DataDrive $dataDrive | Out-Null }
            default         { Write-Error "未知操作: $Action" }
        }
        return
    }

    # 交互模式：菜单循环
    $dataDrive = Find-DataDisk

    while ($true) {
        $steamPath = Find-SteamPath

        Show-Banner
        Show-Menu -DataDrive $dataDrive -SteamPath $steamPath

        $choice = Read-Host "请输入操作编号"

        $needDataDrive = @('1','2','3','4','5','6','7','8','D','d')
        if ($choice -in $needDataDrive -and -not $dataDrive) {
            Write-Host ""
            Write-Warning "数据盘未连接！请先插入数据盘，或选择 [9] 进行首次初始化"
            Write-Host ""
            Read-Host "按回车键继续..."
            $dataDrive = Find-DataDisk
            continue
        }

        switch ($choice) {
            '1' {
                if ($steamPath) { Backup-All -DataDrive $dataDrive -SteamPath $steamPath }
                else { Write-Warning "未找到 Steam，跳过凭证备份"; Backup-GameSaves -DataDrive $dataDrive | Out-Null }
            }
            '2' {
                if ($steamPath) { Restore-All -DataDrive $dataDrive -SteamPath $steamPath }
                else { Write-Warning "未找到 Steam，跳过凭证恢复"; Restore-GameSaves -DataDrive $dataDrive | Out-Null }
            }
            '3' {
                if ($steamPath) { Backup-SteamCredentials -SteamPath $steamPath -DataDrive $dataDrive | Out-Null }
                else { Write-Warning "未找到 Steam 安装路径" }
            }
            '4' {
                if ($steamPath) { Restore-SteamCredentials -SteamPath $steamPath -DataDrive $dataDrive | Out-Null }
                else { Write-Warning "未找到 Steam 安装路径" }
            }
            '5' { Backup-GameSaves -DataDrive $dataDrive | Out-Null }
            '6' { Restore-GameSaves -DataDrive $dataDrive | Out-Null }
            '7' { List-BackupsForGame -DataDrive $dataDrive }
            '8' { Restore-GameSavesWithChoice -DataDrive $dataDrive }
            'D' { Discover-And-Save -DataDrive $dataDrive }
            'd' { Discover-And-Save -DataDrive $dataDrive }
            '9' {
                Write-Host ""
                $selectedDrive = Select-DataDiskInteractive
                if ($selectedDrive) {
                    Initialize-DataDisk -DriveLetter $selectedDrive
                    $dataDrive = $selectedDrive
                }
            }
            '0' {
                Write-Host "再见！" -ForegroundColor Cyan
                return
            }
            default {
                Write-Host "无效的选择，请重新输入" -ForegroundColor Red
            }
        }

        if ($choice -in @('1','2','3','4','5','6','D','d')) {
            # 执行类操作：短暂停留后自动返回
            Write-Host ""
            Start-Sleep -Seconds 2
        }
        elseif ($choice -in @('7','8','9')) {
            # 查看/配置类操作：等待用户确认
            Write-Host ""
            Read-Host "按回车键返回主菜单..."
        }
    }
}

# -----------------------------------------------------------
# 脚本入口（仅在直接运行时调用 Main；GUI 模式下 $Global:GUI_Mode = $true 则跳过）
# -----------------------------------------------------------
if (-not $Global:GUI_Mode) {
    try {
        Main
    }
    catch {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Red
        Write-Host "  未捕获的异常" -ForegroundColor Red
        Write-Host "========================================" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Yellow
        Write-Host $_.ScriptStackTrace -ForegroundColor Gray
        Write-Host ""
        Read-Host "按回车键退出"
    }
}
