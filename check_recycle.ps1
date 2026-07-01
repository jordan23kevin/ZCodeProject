$shell = New-Object -ComObject Shell.Application
$rb = $shell.NameSpace(0xa)
$count = 0
for($i = 0; $i -lt $rb.Items().Count; $i++){
    $item = $rb.Items().Item($i)
    $name = $rb.GetDetailsOf($item, 0)
    if($name -like "*_cut.png"){
        $count++
        $orig = $rb.GetDetailsOf($item, 1)
        Write-Host "$name  (原位置: $orig)"
    }
}
Write-Host "`n回收站中共有 $count 个 _cut.png 文件"
