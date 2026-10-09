param(
    [Parameter(Mandatory=$true)][string]$Docx,
    [Parameter(Mandatory=$true)][string]$Pdf
)

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($Docx, $false, $true)   # ReadOnly
    # 更新所有域，让 SEQ / REF 编号生效
    $doc.Fields.Update() | Out-Null
    foreach ($sec in $doc.Sections) {
        foreach ($h in $sec.Headers) { $h.Range.Fields.Update() | Out-Null }
        foreach ($f in $sec.Footers) { $f.Range.Fields.Update() | Out-Null }
    }
    $doc.Repaginate()
    Write-Output "pages: $($doc.ComputeStatistics(2))"
    Write-Output "words: $($doc.ComputeStatistics(0))"
    $doc.SaveAs2($Pdf, 17)                              # wdFormatPDF
    $doc.Close($false)
    Write-Output "PDF: $Pdf"
} finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
