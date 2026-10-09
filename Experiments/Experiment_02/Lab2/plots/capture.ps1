# capture.ps1 —— 按窗口标题查找窗口、摆位、置顶并截图
#
# 坑一：DPI 缩放。PowerShell 默认非 DPI-aware，高分屏上 GetWindowRect 给的是虚拟化
#       坐标，截图会裁错位置。必须在取矩形之前 SetProcessDPIAware()。
# 坑二：SetForegroundWindow 会被前台锁拒绝，需要 AttachThreadInput 挂到目标线程。
#
# 用法：
#   powershell -File capture.ps1 -TitleMatch "Visual Studio Code" -OutPath shot.png -W 1500 -H 950

param(
    [Parameter(Mandatory=$true)][string]$TitleMatch,
    [Parameter(Mandatory=$true)][string]$OutPath,
    [int]$X = 40, [int]$Y = 30,
    [int]$W = 0, [int]$Ht = 0,
    [int]$WaitMs = 800
)

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;

public class Cap {
    public delegate bool EnumProc(IntPtr h, IntPtr l);

    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)]
    public static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a,
        int x, int y, int cx, int cy, uint flags);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
    [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool f);
    [DllImport("user32.dll")] public static extern IntPtr SetProcessDPIAware();

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int L, T, R, B; }

    public static IntPtr FindWin(string sub) {
        IntPtr found = IntPtr.Zero;
        EnumWindows((h, l) => {
            if (!IsWindowVisible(h)) return true;
            var sb = new StringBuilder(512);
            GetWindowTextW(h, sb, 512);
            if (sb.ToString().IndexOf(sub, StringComparison.OrdinalIgnoreCase) >= 0) {
                found = h; return false;
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }

    public static void Front(IntPtr h) {
        ShowWindow(h, 9);
        uint tpid;
        uint fg = GetWindowThreadProcessId(h, out tpid);
        uint me = GetCurrentThreadId();
        AttachThreadInput(me, fg, true);
        SetForegroundWindow(h);
        AttachThreadInput(me, fg, false);
    }

    // Bring to front WITHOUT SW_RESTORE: calling Front() after a resize
    // would undo the size we just set.
    public static void FrontOnly(IntPtr h) {
        uint tpid;
        uint fg = GetWindowThreadProcessId(h, out tpid);
        uint me = GetCurrentThreadId();
        AttachThreadInput(me, fg, true);
        SetForegroundWindow(h);
        AttachThreadInput(me, fg, false);
    }

    public static int RectX(IntPtr h) { RECT r; GetWindowRect(h, out r); return r.L; }
    public static int RectY(IntPtr h) { RECT r; GetWindowRect(h, out r); return r.T; }
    public static int RectW(IntPtr h) { RECT r; GetWindowRect(h, out r); return r.R - r.L; }
    public static int RectH(IntPtr h) { RECT r; GetWindowRect(h, out r); return r.B - r.T; }

    public static void SizeTo(IntPtr h, int x, int y, int w, int ht) {
        SetWindowPos(h, IntPtr.Zero, x, y, w, ht, 0x0044);   // NOZORDER | SHOWWINDOW
    }
}
"@

[void][Cap]::SetProcessDPIAware()

$win = [Cap]::FindWin($TitleMatch)
if ($win -eq [IntPtr]::Zero) {
    Write-Output "NOT FOUND: $TitleMatch"
    exit 2
}

# 顺序与调用方式都踩过坑：
#   - 先 SW_RESTORE 再 SetWindowPos：SW_RESTORE 会套用窗口保存的还原尺寸
#   - 用 AttachThreadInput 增强置顶：会让窗口把尺寸弹回旧值（实测 1400x65535）
# 现在只做「取消最大化 -> 设尺寸 -> 朴素置顶」三步，实测稳定。
if ($W -gt 0 -and $Ht -gt 0) {
    [void][Cap]::ShowWindow($win, 9)
    Start-Sleep -Milliseconds 300
    [Cap]::SizeTo($win, $X, $Y, $W, $Ht)
    Start-Sleep -Milliseconds 500
}
[void][Cap]::SetForegroundWindow($win)
Start-Sleep -Milliseconds $WaitMs

$rx = [Cap]::RectX($win); $ry = [Cap]::RectY($win)
$rw = [Cap]::RectW($win); $rh = [Cap]::RectH($win)

# GetWindowRect 失败时会返回未初始化的哨兵值（见过 B=65575），必须拦掉
if ($rw -le 0 -or $rh -le 0 -or $rw -gt 8000 -or $rh -gt 8000) {
    Write-Output "BAD RECT: $rx,$ry $rw x $rh"
    exit 3
}

$bmp = New-Object System.Drawing.Bitmap $rw, $rh
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($rx, $ry, 0, 0, (New-Object System.Drawing.Size $rw, $rh))
$bmp.Save($OutPath, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()

Write-Output "OK rect=$rx,$ry ${rw}x${rh} size=$((Get-Item $OutPath).Length)"
