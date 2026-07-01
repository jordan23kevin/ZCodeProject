$s = New-Object -ComObject Shell.Application
$r = $s.NameSpace(0xa)
$c = 0
for($i = 0; $i -lt $r.Items().Count; $i++){
    $it = $r.Items().Item($i)
    $n = $r.GetDetailsOf($it, 0)
    $o = $r.GetDetailsOf($it, 1)
    if($n -like "*DX0165*" -or $o -like "*DX0165*"){
        Write-Host "$n | 原位置: $o"
        $c++
    }
}
Write-Host "共 $c 个"
