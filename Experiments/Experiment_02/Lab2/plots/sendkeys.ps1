# sendkeys.ps1 —— 把按键序列发给指定窗口（用于关掉挡路的弹窗）
param(
    [Parameter(Mandatory=$true)][string]$TitleMatch,
    [Parameter(Mandatory=$true)][string]$Keys,
    [int]$DelayMs = 900
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;using System.Text;using System.Runtime.InteropServices;
public class SK {
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
    [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool f);
    public static IntPtr FindWin(string sub) {
        IntPtr found = IntPtr.Zero;
        EnumWindows((h,l) => {
            if(!IsWindowVisible(h)) return true;
            var sb=new StringBuilder(512); GetWindowTextW(h,sb,512);
            if(sb.ToString().IndexOf(sub,StringComparison.OrdinalIgnoreCase)>=0){ found=h; return false; }
            return true;
        }, IntPtr.Zero);
        return found;
    }
    public static void Front(IntPtr h) {
        ShowWindow(h, 9);
        uint tpid; uint fg = GetWindowThreadProcessId(h, out tpid);
        uint me = GetCurrentThreadId();
        AttachThreadInput(me, fg, true); SetForegroundWindow(h); AttachThreadInput(me, fg, false);
    }
}
"@

$h = [SK]::FindWin($TitleMatch)
if ($h -eq [IntPtr]::Zero) { Write-Output "NOT FOUND"; exit 2 }
[SK]::Front($h)
Start-Sleep -Milliseconds 400
[System.Windows.Forms.SendKeys]::SendWait($Keys)
Start-Sleep -Milliseconds $DelayMs
Write-Output "SENT: $Keys"
