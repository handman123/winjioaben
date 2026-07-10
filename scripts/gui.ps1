# ============================================================
# GameDataKeeper GUI v2.0 — WinForms 界面层
# 职责：UI 渲染、事件处理、调用核心逻辑
# 架构：UI 代码与业务逻辑完全分离，核心函数由 core.ps1 / steam.ps1 提供
# ============================================================

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# 全局错误捕获——弹窗 + 写日志双保险
trap {
    $msg = "初始化失败:`n$($_.Exception.Message)`n`n$($_.ScriptStackTrace)"
    # 写入日志（弹窗可能因窗口句柄问题无法渲染）
    try { $msg | Out-File (Join-Path $ProjectRoot "gui_error.log") -Encoding UTF8 } catch {}
    # 尝试弹窗
    try { [System.Windows.Forms.MessageBox]::Show($msg, "GameDataKeeper 错误", "OK", "Error") } catch {}
    Write-Host $msg
    exit 1
}

# -----------------------------------------------------------
# 初始化：定位脚本目录，加载业务逻辑模块
# -----------------------------------------------------------
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot

. (Join-Path $ScriptRoot "steam.ps1")
$Global:GUI_Mode = $true   # 阻止 core.ps1 运行 CLI 主菜单
. (Join-Path $ScriptRoot "core.ps1")

# 加载游戏配置（失败不阻塞 GUI 启动）
try { Load-GameConfig | Out-Null } catch { $Global:GamesConfig = $null }

# -----------------------------------------------------------
# 全局状态
# -----------------------------------------------------------
$Global:GUI_DataDrive = Find-DataDisk
$Global:GUI_SteamPath = Find-SteamPath

# -----------------------------------------------------------
# 颜色常量（方便统一调整 UI 风格）
# -----------------------------------------------------------
$C_TabActive   = [System.Drawing.Color]::FromArgb(255, 255, 255)
$C_TabInactive = [System.Drawing.Color]::FromArgb(220, 220, 220)
$C_Bg          = [System.Drawing.Color]::FromArgb(245, 245, 245)
$C_Accent      = [System.Drawing.Color]::FromArgb(0, 120, 215)
$C_Success     = [System.Drawing.Color]::FromArgb(0, 150, 0)
$C_Danger      = [System.Drawing.Color]::FromArgb(200, 50, 50)

# -----------------------------------------------------------
# 主窗口
# -----------------------------------------------------------
$Form = New-Object System.Windows.Forms.Form
$Form.Text = "GameDataKeeper v2.0 — 云电脑游戏数据持久化助手"
$Form.Size = New-Object System.Drawing.Size(720, 580)
$Form.StartPosition = "CenterScreen"
$Form.MinimumSize = New-Object System.Drawing.Size(600, 450)
$Form.BackColor = $C_Bg
$Form.FormBorderStyle = "FixedSingle"
$Form.MaximizeBox = $false

# -----------------------------------------------------------
# Tab 栏（顶部横向按钮组）
# -----------------------------------------------------------
$TabBar = New-Object System.Windows.Forms.Panel
$TabBar.Size = New-Object System.Drawing.Size($Form.ClientSize.Width, 36)
$TabBar.Location = New-Object System.Drawing.Point(0, 0)
$TabBar.BackColor = [System.Drawing.Color]::FromArgb(230, 230, 230)
$TabBar.Anchor = "Top,Left,Right"

$Tabs = @{}       # name -> button
$TabPages = @{}   # name -> panel

function New-TabButton {
    param([string]$Text, [string]$Name)
    $btn = New-Object System.Windows.Forms.Button
    $btn.Text = $Text
    $btn.Name = "tab_$Name"
    $btn.FlatStyle = "Flat"
    $btn.FlatAppearance.BorderSize = 0
    $btn.Size = New-Object System.Drawing.Size(100, 36)
    $btn.Font = New-Object System.Drawing.Font("Microsoft YaHei", 10, [System.Drawing.FontStyle]::Regular)
    $btn.BackColor = $C_TabInactive
    $btn.ForeColor = [System.Drawing.Color]::Black
    $btn.Cursor = [System.Windows.Forms.Cursors]::Hand
    $btn.Tag = $Name
    $btn.Add_Click({ On-TabClick $this.Tag })
    return $btn
}

function On-TabClick {
    param([string]$TabName)
    # 切换按钮样式
    foreach ($key in $Tabs.Keys) {
        $Tabs[$key].BackColor = $C_TabInactive
    }
    $Tabs[$TabName].BackColor = $C_TabActive

    # 切换面板
    foreach ($key in $TabPages.Keys) {
        $TabPages[$key].Visible = ($key -eq $TabName)
    }
}

# 创建三个 Tab 按钮
$x = 0
foreach ($tab in @(
    @{Text="Steam";     Name="steam"},
    @{Text="原神";      Name="genshin"},
    @{Text="崩坏:星穹铁道"; Name="starrail"}
)) {
    $btn = New-TabButton -Text $tab.Text -Name $tab.Name
    $btn.Location = New-Object System.Drawing.Point($x, 0)
    $Tabs[$tab.Name] = $btn
    $TabBar.Controls.Add($btn)
    $x += $btn.Width + 1
}

# -----------------------------------------------------------
# 内容面板容器
# -----------------------------------------------------------
$ContentPanel = New-Object System.Windows.Forms.Panel
$ContentPanel.Location = New-Object System.Drawing.Point(0, 36)
$ContentPanel.Size = New-Object System.Drawing.Size($Form.ClientSize.Width, $Form.ClientSize.Height - 36 - 32)
$ContentPanel.Anchor = "Top,Bottom,Left,Right"
$ContentPanel.BackColor = $C_Bg
$ContentPanel.AutoScroll = $true

# -----------------------------------------------------------
# 底部状态栏
# -----------------------------------------------------------
$StatusBar = New-Object System.Windows.Forms.StatusStrip
$StatusLabel = New-Object System.Windows.Forms.ToolStripStatusLabel
$StatusLabel.Text = "就绪"
$StatusLabel.ForeColor = [System.Drawing.Color]::Gray
$StatusBar.Items.Add($StatusLabel)

# 右侧进度条
$ProgressBar = New-Object System.Windows.Forms.ToolStripProgressBar
$ProgressBar.Style = "Marquee"
$ProgressBar.Visible = $false
$ProgressBar.Size = New-Object System.Drawing.Size(120, 16)
$StatusBar.Items.Add($ProgressBar)

$Form.Controls.Add($StatusBar)

# -----------------------------------------------------------
# 辅助函数：状态栏控制
# -----------------------------------------------------------
function Set-Status {
    param([string]$Text, [string]$Color = "Gray")
    $StatusLabel.Text = $Text
    $StatusLabel.ForeColor = switch ($Color) {
        "green"  { $C_Success }
        "red"    { $C_Danger }
        "blue"   { $C_Accent }
        default  { [System.Drawing.Color]::Gray }
    }
}

function Show-Progress { $ProgressBar.Visible = $true }
function Hide-Progress { $ProgressBar.Visible = $false }

function Set-ButtonsEnabled {
    param([bool]$Enabled)
    foreach ($ctrl in ($CurrentActionButtons + $TabBar.Controls)) {
        $ctrl.Enabled = $Enabled
    }
}

# -----------------------------------------------------------
# 共享数据刷新
# -----------------------------------------------------------
function Refresh-Status {
    $Global:GUI_DataDrive = Find-DataDisk
    $Global:GUI_SteamPath = Find-SteamPath
}

# -----------------------------------------------------------
# 无阻塞执行操作（显示进度条，UI 不卡死）
# -----------------------------------------------------------
function Invoke-WithProgress {
    param([scriptblock]$Action, [string]$WorkingMessage = "处理中...")

    Set-ButtonsEnabled $false
    Set-Status $WorkingMessage "blue"
    Show-Progress

    try {
        $result = & $Action
    }
    catch {
        Set-Status "错误: $($_.Exception.Message)" "red"
        Hide-Progress
        Set-ButtonsEnabled $true
        return $false
    }

    Hide-Progress
    Refresh-Status
    Update-SteamTabInfo  # 刷新 Steam 页面的状态信息
    Set-ButtonsEnabled $true
    return $result
}

# -----------------------------------------------------------
# GUI 包装函数（处理核心逻辑中 Read-Host 的交互，转为 MessageBox）
# -----------------------------------------------------------

# 包装：Steam 凭证恢复（处理"Steam 正在运行"的确认弹窗）
function GUI-RestoreSteam {
    if (-not $Global:GUI_SteamPath) {
        [System.Windows.Forms.MessageBox]::Show("未找到 Steam 安装路径", "错误", "OK", "Error")
        return $false
    }
    if (-not $Global:GUI_DataDrive) {
        [System.Windows.Forms.MessageBox]::Show("数据盘未连接", "错误", "OK", "Error")
        return $false
    }

    if (Test-SteamRunning) {
        $r = [System.Windows.Forms.MessageBox]::Show(
            "Steam 正在运行，需要关闭后才能恢复凭证。`n`n是否关闭 Steam 并继续？",
            "Steam 正在运行", "YesNo", "Question"
        )
        if ($r -eq "Yes") {
            Stop-SteamIfRunning | Out-Null
        } else {
            Set-Status "已取消" "gray"
            return $false
        }
    }

    $result = Restore-SteamCredentials -SteamPath $Global:GUI_SteamPath -DataDrive $Global:GUI_DataDrive
    if ($result) { Set-Status "Steam 凭证恢复完成" "green" }
    return $result
}

# 包装：恢复全部（先处理 Steam 运行确认，再执行恢复）
function GUI-RestoreAll {
    if (Test-SteamRunning) {
        $r = [System.Windows.Forms.MessageBox]::Show(
            "Steam 正在运行，需要关闭后才能恢复凭证。`n`n是否关闭 Steam 并继续？",
            "Steam 正在运行", "YesNo", "Question"
        )
        if ($r -eq "Yes") {
            Stop-SteamIfRunning | Out-Null
        } else {
            Set-Status "已取消" "gray"
            return $false
        }
    }

    Restore-All -DataDrive $Global:GUI_DataDrive -SteamPath $Global:GUI_SteamPath
    Set-Status "全部恢复完成" "green"
    return $true
}

# 包装：发现存档（处理 Read-Host 交互）
function GUI-DiscoverSaves {
    if (-not $Global:GUI_DataDrive) {
        [System.Windows.Forms.MessageBox]::Show("数据盘未连接", "错误", "OK", "Error")
        return
    }
    if (-not $Global:GUI_SteamPath) {
        [System.Windows.Forms.MessageBox]::Show("未找到 Steam。`n`n请确保 Steam 已安装并至少运行过一次。", "错误", "OK", "Error")
        return
    }

    # 检测运行中的游戏
    $game = $null
    $procs = Get-Process -ErrorAction SilentlyContinue
    foreach ($p in $procs) {
        try { $exe = $p.MainModule.FileName } catch { continue }
        if ($exe -match '\\steamapps\\common\\([^\\]+)') {
            $folderName = $Matches[1]
            if ($exe -match '^(.+?\\steamapps\\common\\[^\\]+)') {
                $game = @{ Folder = $folderName; Root = $Matches[1] }
                break
            }
        }
    }

    if (-not $game) {
        [System.Windows.Forms.MessageBox]::Show(
            "未检测到正在运行的 Steam 游戏。`n`n请先启动游戏，再点击 [发现存档]。",
            "未检测到游戏", "OK", "Information"
        )
        return
    }

    # 确认
    $r = [System.Windows.Forms.MessageBox]::Show(
        "检测到游戏: $($game.Folder)`n安装路径: $($game.Root)`n`n是否自动搜索存档目录并保存配置？",
        "确认发现", "YesNo", "Question"
    )
    if ($r -ne "Yes") { return }

    # 搜索存档
    $saveDirs = @()
    Get-ChildItem $game.Root -Directory -Recurse -Depth 4 -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_.Name -match '^(SaveFiles|SaveGames|Save|Saves|SaveData|Saved|saves|save)$') {
            $fc = @(Get-ChildItem $_.FullName -File -Recurse -ErrorAction SilentlyContinue).Count
            if ($fc -gt 0) {
                $saveDirs += @{ name = $_.Name; path = $_.FullName; files = $fc }
            }
        }
    }

    if ($saveDirs.Count -eq 0) {
        [System.Windows.Forms.MessageBox]::Show(
            "未自动发现存档目录。`n`n请确认游戏目录下存在存档文件夹（如 SaveGames、SaveFiles 等）。",
            "未发现存档", "OK", "Warning"
        )
        return
    }

    # 写入配置
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
        comment = "存档路径由 GUI 自动发现"
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

    # 创建备份目录
    $backupBase = Join-Path $Global:GUI_DataDrive "GameDataKeeper\Saves\$safeName"
    foreach ($s in $saveDirs) {
        $d = Join-Path $backupBase $s.name
        if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
    }

    [System.Windows.Forms.MessageBox]::Show(
        "发现完成！`n`n游戏: $($game.Folder)`n存档: $($saveDirs.Count) 个目录`n`n现在可以备份/恢复了。",
        "发现完成", "OK", "Information"
    )
    Update-SteamTabInfo
}

# -----------------------------------------------------------
# GUI 包装函数（处理核心逻辑中 Read-Host 的交互，转为 MessageBox）
# -----------------------------------------------------------
$PageSteam = New-Object System.Windows.Forms.Panel
$PageSteam.Size = $ContentPanel.ClientSize
$PageSteam.BackColor = $C_Bg
$PageSteam.AutoScroll = $true
$PageSteam.Anchor = "Top,Bottom,Left,Right"

$TabPages["steam"] = $PageSteam

$y = 10; $pad = 10; $lblW = 80; $valW = $PageSteam.Width - $lblW - 40

# --- 状态信息区 ---
$grpInfo = New-Object System.Windows.Forms.GroupBox
$grpInfo.Text = "系统状态"
$grpInfo.Location = New-Object System.Drawing.Point($pad, $y)
$grpInfo.Size = New-Object System.Drawing.Size($PageSteam.Width - 24, 85)
$grpInfo.Font = New-Object System.Drawing.Font("Microsoft YaHei", 9)
$PageSteam.Controls.Add($grpInfo)

$lblDataDrive = New-Object System.Windows.Forms.Label
$lblDataDrive.Text = "数据盘: 检测中..."
$lblDataDrive.Location = New-Object System.Drawing.Point(10, 20)
$lblDataDrive.AutoSize = $true
$grpInfo.Controls.Add($lblDataDrive)

$lblSteamPath = New-Object System.Windows.Forms.Label
$lblSteamPath.Text = "Steam: 检测中..."
$lblSteamPath.Location = New-Object System.Drawing.Point(10, 42)
$lblSteamPath.AutoSize = $true
$grpInfo.Controls.Add($lblSteamPath)

$btnDiscover = New-Object System.Windows.Forms.Button
$btnDiscover.Text = "发现存档"
$btnDiscover.Size = New-Object System.Drawing.Size(80, 26)
$btnDiscover.Location = New-Object System.Drawing.Point(10, 58)
$btnDiscover.FlatStyle = "Flat"
$btnDiscover.BackColor = [System.Drawing.Color]::FromArgb(200, 200, 200)
$btnDiscover.Add_Click({
    Invoke-WithProgress {
        GUI-DiscoverSaves
    } "正在扫描游戏存档..."
    Update-SteamTabInfo
})
$grpInfo.Controls.Add($btnDiscover)

function Update-SteamTabInfo {
    $dd = $Global:GUI_DataDrive
    $sp = $Global:GUI_SteamPath

    if ($dd) {
        $lblDataDrive.Text = "数据盘: $dd (已连接)"
        $lblDataDrive.ForeColor = $C_Success
    } else {
        $lblDataDrive.Text = "数据盘: 未检测到 (请先初始化 [9] 或插入数据盘)"
        $lblDataDrive.ForeColor = $C_Danger
    }

    if ($sp) {
        $lblSteamPath.Text = "Steam: $sp"
        $lblSteamPath.ForeColor = $C_Success
    } else {
        $lblSteamPath.Text = "Steam: 未找到"
        $lblSteamPath.ForeColor = $C_Danger
    }

    # 更新游戏存档状态
    if ($Global:GamesConfig -and $Global:GamesConfig.games -and $Global:GamesConfig.games.Count -gt 0) {
        $g = $Global:GamesConfig.games[0]
        $sp = $g.save_paths[0]
        $exists = Test-Path $sp.path
        $lblSaveStatus.Text = if ($exists) { "存档目录: $($sp.path) (存在)" } else { "存档目录: 尚未创建" }
        $lblSaveStatus.ForeColor = if ($exists) { $C_Success } else { [System.Drawing.Color]::DarkOrange }
        $btnDiscover.Text = "重新发现"
    } else {
        $lblSaveStatus.Text = "存档目录: 未配置（请先启动游戏后点击 [发现存档]）"
        $lblSaveStatus.ForeColor = $C_Danger
    }

    # 更新历史列表
    Update-HistoryList
}

$lblSaveStatus = New-Object System.Windows.Forms.Label
$lblSaveStatus.Text = "存档目录: 未配置"
$lblSaveStatus.Location = New-Object System.Drawing.Point(100, 62)
$lblSaveStatus.AutoSize = $true
$grpInfo.Controls.Add($lblSaveStatus)

$y += $grpInfo.Height + $pad

# --- 操作按钮区 ---
$grpActions = New-Object System.Windows.Forms.GroupBox
$grpActions.Text = "快捷操作"
$grpActions.Location = New-Object System.Drawing.Point($pad, $y)
$grpActions.Size = New-Object System.Drawing.Size($PageSteam.Width - 24, 105)
$grpActions.Font = New-Object System.Drawing.Font("Microsoft YaHei", 9)
$PageSteam.Controls.Add($grpActions)

$btnW = 130; $btnH = 32; $gap = 8
$btnX = 10; $btnY = 22

function New-ActionButton {
    param([string]$Text, [scriptblock]$Action, [string]$Tooltip = "")
    $b = New-Object System.Windows.Forms.Button
    $b.Text = $Text
    $b.Size = New-Object System.Drawing.Size($btnW, $btnH)
    $b.FlatStyle = "Flat"
    $b.BackColor = [System.Drawing.Color]::White
    $b.Font = New-Object System.Drawing.Font("Microsoft YaHei", 9)
    $b.Add_Click($Action)
    if ($Tooltip) {
        $tt = New-Object System.Windows.Forms.ToolTip
        $tt.SetToolTip($b, $Tooltip)
    }
    return $b
}

# 第一行：备份/恢复全部
$btnBackupAll = New-ActionButton "备份全部" {
    Invoke-WithProgress {
        Backup-All -DataDrive $Global:GUI_DataDrive -SteamPath $Global:GUI_SteamPath
    } "正在备份全部数据..."
    Set-Status "备份完成" "green"
}
$btnBackupAll.Location = New-Object System.Drawing.Point($btnX, $btnY)
$grpActions.Controls.Add($btnBackupAll)

$btnRestoreAll = New-ActionButton "恢复全部" {
    Invoke-WithProgress {
        GUI-RestoreAll
    } "正在恢复全部数据..."
    Set-Status "恢复完成" "green"
}
$btnRestoreAll.Location = New-Object System.Drawing.Point($btnX + $btnW + $gap, $btnY)
$grpActions.Controls.Add($btnRestoreAll)

# 第二行：单独操作
$btnBackupSteam = New-ActionButton "备份 Steam 凭证" {
    Invoke-WithProgress {
        Backup-SteamCredentials -SteamPath $Global:GUI_SteamPath -DataDrive $Global:GUI_DataDrive
    } "正在备份 Steam 凭证..."
    Set-Status "Steam 凭证已备份" "green"
}
$btnBackupSteam.Location = New-Object System.Drawing.Point($btnX, $btnY + $btnH + 4)
$grpActions.Controls.Add($btnBackupSteam)

$btnRestoreSteam = New-ActionButton "恢复 Steam 凭证" {
    Invoke-WithProgress {
        GUI-RestoreSteam
    } "正在恢复 Steam 凭证..."
    Set-Status "Steam 凭证已恢复" "green"
}
$btnRestoreSteam.Location = New-Object System.Drawing.Point($btnX + $btnW + $gap, $btnY + $btnH + 4)
$grpActions.Controls.Add($btnRestoreSteam)

$btnBackupSaves = New-ActionButton "备份游戏存档" {
    Invoke-WithProgress {
        Backup-GameSaves -DataDrive $Global:GUI_DataDrive
    } "正在备份游戏存档..."
    Update-HistoryList
    Set-Status "游戏存档已备份" "green"
}
$btnBackupSaves.Location = New-Object System.Drawing.Point($btnX + 2 * ($btnW + $gap), $btnY)
$grpActions.Controls.Add($btnBackupSaves)

$btnRestoreSaves = New-ActionButton "恢复最新存档" {
    Invoke-WithProgress {
        Restore-GameSaves -DataDrive $Global:GUI_DataDrive
    } "正在恢复游戏存档..."
    Set-Status "游戏存档已恢复" "green"
}
$btnRestoreSaves.Location = New-Object System.Drawing.Point($btnX + 2 * ($btnW + $gap), $btnY + $btnH + 4)
$grpActions.Controls.Add($btnRestoreSaves)

# 全局按钮列表（用于在操作期间禁用）
$CurrentActionButtons = @(
    $btnBackupAll, $btnRestoreAll,
    $btnBackupSteam, $btnRestoreSteam,
    $btnBackupSaves, $btnRestoreSaves,
    $btnDiscover
)

$y += $grpActions.Height + $pad

# --- 存档历史区 ---
$grpHistory = New-Object System.Windows.Forms.GroupBox
$grpHistory.Text = "存档历史"
$grpHistory.Location = New-Object System.Drawing.Point($pad, $y)
$grpHistory.Size = New-Object System.Drawing.Size($PageSteam.Width - 24, 195)
$grpHistory.Font = New-Object System.Drawing.Font("Microsoft YaHei", 9)
$PageSteam.Controls.Add($grpHistory)

$lstHistory = New-Object System.Windows.Forms.ListView
$lstHistory.Location = New-Object System.Drawing.Point(10, 20)
$lstHistory.Size = New-Object System.Drawing.Size($grpHistory.Width - 130, 145)
$lstHistory.View = "Details"
$lstHistory.FullRowSelect = $true
$lstHistory.GridLines = $true
$lstHistory.MultiSelect = $false
$lstHistory.Columns.Add("时间", 140)
$lstHistory.Columns.Add("类型", 80)
$lstHistory.Columns.Add("大小", 80)
$grpHistory.Controls.Add($lstHistory)

$btnRestoreSelected = New-Object System.Windows.Forms.Button
$btnRestoreSelected.Text = "恢复选中"
$btnRestoreSelected.Size = New-Object System.Drawing.Size(100, 28)
$btnRestoreSelected.Location = New-Object System.Drawing.Point($lstHistory.Right + 10, 20)
$btnRestoreSelected.FlatStyle = "Flat"
$btnRestoreSelected.BackColor = [System.Drawing.Color]::White
$btnRestoreSelected.Add_Click({
    if (-not $lstHistory.SelectedItems -or $lstHistory.SelectedItems.Count -eq 0) {
        [System.Windows.Forms.MessageBox]::Show("请先选择一个备份", "提示")
        return
    }
    $item = $lstHistory.SelectedItems[0]
    $zipName = $item.SubItems[0].Text
    $saveName = $item.SubItems[1].Text
    $game = $Global:GamesConfig.games[0]
    $saveRoot = Join-Path $Global:GUI_DataDrive "GameDataKeeper\Saves"
    $backupDir = Join-Path $saveRoot "$($game.backup_dir)\$saveName"

    # 解析存档路径
    $foundPaths = Get-GameSavePaths -Game $game -SteamPath $Global:GUI_SteamPath -ForRestore
    $targetPath = if ($foundPaths.Count -gt 0) { $foundPaths[0].Path } else { "" }

    if ($targetPath -eq "") {
        [System.Windows.Forms.MessageBox]::Show("无法确定存档恢复路径", "错误")
        return
    }

    Invoke-WithProgress {
        Restore-SavePath -SavePath $targetPath -BackupBaseDir $backupDir -Label "$($game.name)\$saveName" -SpecificBackup $zipName
    } "正在恢复存档..."
    Set-Status "存档恢复完成" "green"
})
$grpHistory.Controls.Add($btnRestoreSelected)

$btnRefreshHistory = New-Object System.Windows.Forms.Button
$btnRefreshHistory.Text = "刷新列表"
$btnRefreshHistory.Size = New-Object System.Drawing.Size(100, 28)
$btnRefreshHistory.Location = New-Object System.Drawing.Point($lstHistory.Right + 10, 55)
$btnRefreshHistory.FlatStyle = "Flat"
$btnRefreshHistory.BackColor = [System.Drawing.Color]::White
$btnRefreshHistory.Add_Click({ Update-HistoryList })
$grpHistory.Controls.Add($btnRefreshHistory)

function Update-HistoryList {
    $lstHistory.Items.Clear()
    if (-not $Global:GUI_DataDrive -or -not $Global:GamesConfig -or -not $Global:GamesConfig.games) { return }

    $saveRoot = Join-Path $Global:GUI_DataDrive "GameDataKeeper\Saves"
    foreach ($game in $Global:GamesConfig.games) {
        $baseDir = Join-Path $saveRoot $game.backup_dir
        if (-not (Test-Path $baseDir)) { continue }

        Get-ChildItem $baseDir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            $saveDir = $_.FullName
            Get-ChildItem $saveDir -Filter "*.zip" -File -ErrorAction SilentlyContinue | Sort-Object Name -Descending | ForEach-Object {
                $item = New-Object System.Windows.Forms.ListViewItem($_.Name)
                $item.SubItems.Add($_.Directory.Name)
                $item.SubItems.Add("$([math]::Round($_.Length / 1KB, 0)) KB")
                $lstHistory.Items.Add($item)
            }
        }
    }

    if ($lstHistory.Items.Count -gt 0) {
        $lstHistory.Items[0].Selected = $true
    }
}

# -----------------------------------------------------------
# ==================== 原神 Tab（占位） ======================
# -----------------------------------------------------------
$PageGenshin = New-Object System.Windows.Forms.Panel
$PageGenshin.Size = $ContentPanel.ClientSize
$PageGenshin.BackColor = $C_Bg
$TabPages["genshin"] = $PageGenshin

$lblGenshin = New-Object System.Windows.Forms.Label
$lblGenshin.Text = "原神 — 功能开发中`n`n后续将支持：`n  • 原神账号凭证备份与恢复`n  • 游戏截图备份"
$lblGenshin.Location = New-Object System.Drawing.Point(60, 80)
$lblGenshin.AutoSize = $true
$lblGenshin.Font = New-Object System.Drawing.Font("Microsoft YaHei", 11)
$lblGenshin.ForeColor = [System.Drawing.Color]::Gray
$PageGenshin.Controls.Add($lblGenshin)

# -----------------------------------------------------------
# ==================== 崩铁 Tab（占位） ======================
# -----------------------------------------------------------
$PageStarRail = New-Object System.Windows.Forms.Panel
$PageStarRail.Size = $ContentPanel.ClientSize
$PageStarRail.BackColor = $C_Bg
$TabPages["starrail"] = $PageStarRail

$lblStarRail = New-Object System.Windows.Forms.Label
$lblStarRail.Text = "崩坏:星穹铁道 — 功能开发中`n`n后续将支持：`n  • 崩铁账号凭证备份与恢复`n  • 游戏截图备份"
$lblStarRail.Location = New-Object System.Drawing.Point(60, 80)
$lblStarRail.AutoSize = $true
$lblStarRail.Font = New-Object System.Drawing.Font("Microsoft YaHei", 11)
$lblStarRail.ForeColor = [System.Drawing.Color]::Gray
$PageStarRail.Controls.Add($lblStarRail)

# -----------------------------------------------------------
# 组装：Tab 面板加入 ContentPanel
# -----------------------------------------------------------
foreach ($panel in $TabPages.Values) {
    $panel.Dock = "Fill"
    $ContentPanel.Controls.Add($panel)
}

# -----------------------------------------------------------
# 组装主窗口
# -----------------------------------------------------------
$Form.Controls.Add($ContentPanel)
$Form.Controls.Add($TabBar)

# -----------------------------------------------------------
# 初始化状态
# -----------------------------------------------------------
On-TabClick "steam"     # 默认选中 Steam
Update-SteamTabInfo

# 窗口关闭事件
$Form.Add_FormClosing({
    # 清理：无特殊资源需要释放
})

# -----------------------------------------------------------
# 启动主窗口
# -----------------------------------------------------------
try {
    $Form.ShowDialog() | Out-Null
}
catch {
    $msg = "运行时错误:`n$($_.Exception.Message)"
    try { $msg | Out-File (Join-Path $ProjectRoot "gui_error.log") -Encoding UTF8 } catch {}
    try { [System.Windows.Forms.MessageBox]::Show($msg, "GameDataKeeper 错误", "OK", "Error") } catch {}
    Write-Host $msg
}
