# 打印实验一（连续 GA）的输入输出文件内容，供报告截图使用
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "===== gadata.txt（连续 GA 的变量上下界）=====" -ForegroundColor Cyan
Get-Content gadata.txt

Write-Host ""
Write-Host "===== output.dat（前 5 行：代数, x1, x2, 适应度）=====" -ForegroundColor Cyan
Get-Content output.dat -TotalCount 5

Write-Host ""
Write-Host "===== galog.txt（前 8 行：逐代最优/平均/标准差）=====" -ForegroundColor Cyan
Get-Content galog.txt -TotalCount 8
