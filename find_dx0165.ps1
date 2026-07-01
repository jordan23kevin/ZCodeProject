$s = New-Object -ComObject Shell.Application
$r = $s.NameSpace(0xa)
for($i=0; $i -lt $r.Items().Count; $i++){
    $it = $r.Items().Item($i)
    $n = $r.GetDetailsOf($it, 0)
    $o = $r.GetDetailsOf($it, 1)
    if($n -match "DX0165" -or $o -match "DX0165"){
        Write-Host ($n + "|" + $o)
    }
}
