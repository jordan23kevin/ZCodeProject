
$s = New-Object -ComObject Shell.Application
$r = $s.NameSpace(0xa)
$found = @()
for($i=0; $i -lt $r.Items().Count; $i++){
    $it = $r.Items().Item($i)
    $n = $r.GetDetailsOf($it, 0)
    $o = $r.GetDetailsOf($it, 1)
    if($n -match "DX0167_B" -or $o -match "DX0167_B"){
        Write-Host ($n + "|" + $o)
        $found += 1
    }
}
if($found.Count -eq 0){ Write-Host "NOTFOUND" }
