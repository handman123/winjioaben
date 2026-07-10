# ============================================================
# Steam 凭证处理模块
# 职责：Steam 登录凭证的备份与恢复
# 后续迭代：该模块可被 GUI 或命令行直接调用
# ============================================================

# -----------------------------------------------------------
# 查找 Steam 安装路径
# 返回：Steam 安装目录的完整路径，未找到则返回 $null
# -----------------------------------------------------------
function Find-SteamPath {
    # 策略1：通过注册表查找（64位系统）
    try {
        $path = (Get-ItemProperty -Path "HKLM:\SOFTWARE\WOW6432Node\Valve\Steam" -Name "InstallPath" -ErrorAction Stop).InstallPath
        if (Test-Path $path) {
            Write-Verbose "通过注册表找到 Steam: $path"
            return $path
        }
    }
    catch {
        Write-Verbose "注册表查找失败 (WOW6432Node)"
    }

    # 策略2：通过注册表查找（32位系统）
    try {
        $path = (Get-ItemProperty -Path "HKLM:\SOFTWARE\Valve\Steam" -Name "InstallPath" -ErrorAction Stop).InstallPath
        if (Test-Path $path) {
            Write-Verbose "通过注册表找到 Steam: $path"
            return $path
        }
    }
    catch {
        Write-Verbose "注册表查找失败 (SOFTWARE)"
    }

    # 策略3：尝试默认安装路径
    $defaultPaths = @(
        "C:\Program Files (x86)\Steam",
        "D:\Program Files (x86)\Steam",
        "C:\Steam",
        "D:\Steam"
    )
    foreach ($dp in $defaultPaths) {
        if (Test-Path $dp) {
            Write-Verbose "通过默认路径找到 Steam: $dp"
            return $dp
        }
    }

    Write-Verbose "未能找到 Steam 安装路径"
    return $null
}

# -----------------------------------------------------------
# 检查 Steam 是否正在运行
# 返回：$true 表示正在运行
# -----------------------------------------------------------
function Test-SteamRunning {
    $proc = Get-Process -Name "steam" -ErrorAction SilentlyContinue
    return ($null -ne $proc)
}

# -----------------------------------------------------------
# 停止 Steam 进程（如果需要）
# -----------------------------------------------------------
function Stop-SteamIfRunning {
    if (Test-SteamRunning) {
        Write-Warning "检测到 Steam 正在运行，正在尝试关闭..."
        try {
            Stop-Process -Name "steam" -Force -ErrorAction Stop
            Start-Sleep -Seconds 3
            Write-Host "  Steam 已关闭" -ForegroundColor Green
            return $true
        }
        catch {
            Write-Error "无法关闭 Steam，请手动退出 Steam 后重试"
            return $false
        }
    }
    return $true
}

# -----------------------------------------------------------
# 备份 Steam 登录凭证
# 参数：
#   $SteamPath  - Steam 安装路径
#   $DataDrive  - 数据盘盘符（如 "E:"）
# 返回：$true 成功，$false 失败
# -----------------------------------------------------------
function Backup-SteamCredentials {
    param(
        [Parameter(Mandatory=$true)]
        [string]$SteamPath,

        [Parameter(Mandatory=$true)]
        [string]$DataDrive
    )

    Write-Host ""
    Write-Host "========== 备份 Steam 登录凭证 ==========" -ForegroundColor Cyan

    $backupRoot = Join-Path $DataDrive "GameDataKeeper\Steam"
    $backupConfig = Join-Path $backupRoot "config"
    $backupSsfn = Join-Path $backupRoot "ssfn"
    $backupReg = Join-Path $backupRoot "registry.reg"

    # 创建备份目录
    foreach ($d in @($backupConfig, $backupSsfn)) {
        if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
    }

    $allSuccess = $true

    # --- 1. 备份 SSFN 文件（机器信任凭证，"记住此电脑"的关键） ---
    $ssfnFiles = Get-ChildItem -Path $SteamPath -Filter "ssfn*" -File -ErrorAction SilentlyContinue
    if ($ssfnFiles.Count -gt 0) {
        foreach ($f in $ssfnFiles) {
            try {
                Copy-Item -Path $f.FullName -Destination $backupSsfn -Force
                Write-Host "  [OK] 已备份: $($f.Name)" -ForegroundColor Green
            }
            catch {
                Write-Host "  [FAIL] 备份失败: $($f.Name) — $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
    else {
        Write-Host "  [INFO] 未找到 SSFN 文件（首次登录后才会生成）" -ForegroundColor Gray
    }

    # --- 2. 备份 config 文件 ---
    $steamConfig = Join-Path $SteamPath "config"
    $filesToBackup = @("loginusers.vdf", "config.vdf")

    foreach ($file in $filesToBackup) {
        $sourceFile = Join-Path $steamConfig $file
        if (Test-Path $sourceFile) {
            try {
                Copy-Item -Path $sourceFile -Destination $backupConfig -Force
                Write-Host "  [OK] 已备份: $file" -ForegroundColor Green
            }
            catch {
                Write-Host "  [FAIL] 备份失败: $file — $($_.Exception.Message)" -ForegroundColor Red
                $allSuccess = $false
            }
        }
        else {
            Write-Host "  [SKIP] 源文件不存在: $file" -ForegroundColor Yellow
        }
    }

    # --- 3. 备份注册表 ---
    try {
        $regArgs = @(
            "export",
            "HKCU\Software\Valve\Steam",
            $backupReg,
            "/y"
        )
        $result = & reg.exe $regArgs 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] 已备份注册表: HKCU\Software\Valve\Steam" -ForegroundColor Green
        }
        else {
            Write-Host "  [WARN] 注册表备份可能不完整: $result" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "  [WARN] 注册表备份失败: $($_.Exception.Message)" -ForegroundColor Yellow
        # 注册表备份失败不算致命错误
    }

    if ($allSuccess) {
        Write-Host "Steam 凭证备份完成" -ForegroundColor Green
    }
    return $allSuccess
}

# -----------------------------------------------------------
# 恢复 Steam 登录凭证
# 参数：
#   $SteamPath  - Steam 安装路径
#   $DataDrive  - 数据盘盘符
# 返回：$true 成功，$false 失败
# -----------------------------------------------------------
function Restore-SteamCredentials {
    param(
        [Parameter(Mandatory=$true)]
        [string]$SteamPath,

        [Parameter(Mandatory=$true)]
        [string]$DataDrive
    )

    Write-Host ""
    Write-Host "========== 恢复 Steam 登录凭证 ==========" -ForegroundColor Cyan

    # 先确保 Steam 已关闭
    $wasRunning = $false
    if (Test-SteamRunning) {
        $choice = Read-Host "Steam 正在运行，需要关闭才能恢复凭证。是否关闭 Steam? (Y/n)"
        if ($choice -eq '' -or $choice -eq 'y' -or $choice -eq 'Y') {
            if (-not (Stop-SteamIfRunning)) {
                return $false
            }
            $wasRunning = $true
        }
        else {
            Write-Warning "已取消：恢复凭证需要 Steam 处于关闭状态"
            return $false
        }
    }

    $backupRoot = Join-Path $DataDrive "GameDataKeeper\Steam"
    $backupConfig = Join-Path $backupRoot "config"
    $backupSsfn = Join-Path $backupRoot "ssfn"
    $backupReg = Join-Path $backupRoot "registry.reg"

    # 检查备份是否存在
    $hasConfig = Test-Path $backupConfig
    $hasSsfn = (Test-Path $backupSsfn) -and ((Get-ChildItem $backupSsfn -File -ErrorAction SilentlyContinue).Count -gt 0)
    if (-not $hasConfig -and -not $hasSsfn) {
        Write-Error "未找到 Steam 凭证备份，请先执行备份操作"
        return $false
    }

    $allSuccess = $true

    # --- 1. 恢复 SSFN 文件（机器信任凭证） ---
    if ($hasSsfn) {
        Get-ChildItem $backupSsfn -File | ForEach-Object {
            try {
                Copy-Item -Path $_.FullName -Destination $SteamPath -Force
                Write-Host "  [OK] 已恢复: $($_.Name)" -ForegroundColor Green
            }
            catch {
                Write-Host "  [FAIL] 恢复失败: $($_.Name)" -ForegroundColor Red
                $allSuccess = $false
            }
        }
    }

    # --- 2. 恢复 config 文件 ---
    $steamConfig = Join-Path $SteamPath "config"

    # 确保本地 config 目录存在
    if (-not (Test-Path $steamConfig)) {
        New-Item -ItemType Directory -Path $steamConfig -Force | Out-Null
    }

    $filesToRestore = @("loginusers.vdf", "config.vdf")
    foreach ($file in $filesToRestore) {
        $sourceFile = Join-Path $backupConfig $file
        if (Test-Path $sourceFile) {
            try {
                Copy-Item -Path $sourceFile -Destination $steamConfig -Force
                Write-Host "  [OK] 已恢复: $file" -ForegroundColor Green
            }
            catch {
                Write-Host "  [FAIL] 恢复失败: $file — $($_.Exception.Message)" -ForegroundColor Red
                $allSuccess = $false
            }
        }
        else {
            Write-Host "  [SKIP] 备份中无此文件: $file" -ForegroundColor Yellow
        }
    }

    # --- 3. 恢复注册表 ---
    if (Test-Path $backupReg) {
        try {
            $result = & reg.exe import $backupReg 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [OK] 已恢复注册表" -ForegroundColor Green
            }
            else {
                Write-Host "  [WARN] 注册表恢复可能不完整: $result" -ForegroundColor Yellow
            }
        }
        catch {
            Write-Host "  [WARN] 注册表恢复失败: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "  [SKIP] 无注册表备份文件" -ForegroundColor Yellow
    }

    if ($allSuccess) {
        Write-Host ""
        Write-Host "Steam 凭证恢复完成！" -ForegroundColor Green
        if ($wasRunning) {
            Write-Host "正在重新启动 Steam..." -ForegroundColor Gray
            $steamExe = Join-Path $SteamPath "steam.exe"
            if (Test-Path $steamExe) {
                Start-Process -FilePath $steamExe
                Write-Host "Steam 已启动，请稍候查看登录状态" -ForegroundColor Green
            }
            else {
                Write-Host "未找到 steam.exe，请手动启动 Steam" -ForegroundColor Yellow
            }
        }
        else {
            Write-Host "请手动启动 Steam 验证登录状态" -ForegroundColor Gray
        }
    }
    return $allSuccess
}

# -----------------------------------------------------------
# 此文件通过 dot-source 方式加载（. "steam.ps1"）
# 所有函数自动导入到调用方作用域，无需 Export-ModuleMember
# -----------------------------------------------------------
