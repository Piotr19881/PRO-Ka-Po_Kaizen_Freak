# ============================================================================
# Skrypt czyszczący dane testowe z bazy
# ============================================================================

$baseUrl = "http://127.0.0.1:8000"

# Wczytaj token
$token = Get-Content -Path "token.txt" -Raw
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

Write-Host "`n╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   CZYSZCZENIE DANYCH TESTOWYCH             ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Pobierz wszystkie dane
try {
    $allData = Invoke-RestMethod -Uri "$baseUrl/api/pomodoro/all" -Method Get -Headers $headers
    
    Write-Host "Znaleziono:" -ForegroundColor Yellow
    Write-Host "  Tematy: $($allData.topics.Count)" -ForegroundColor Gray
    Write-Host "  Sesje: $($allData.sessions.Count)" -ForegroundColor Gray
    
    # Usuń sesje testowe
    foreach ($session in $allData.sessions) {
        if ($session.local_id -like "*test*") {
            try {
                $deleteUrl = "$baseUrl/api/pomodoro/sessions/$($session.server_id)?version=$($session.version)"
                Write-Host "`nUsuwam sesję: $($session.local_id)" -ForegroundColor Yellow
                Write-Host "  URL: $deleteUrl" -ForegroundColor Gray
                $result = Invoke-RestMethod -Uri $deleteUrl -Method Delete -Headers $headers
                Write-Host "  ✓ Usunięto" -ForegroundColor Green
            } catch {
                Write-Host "  ✗ Błąd: $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
    
    # Usuń tematy testowe
    foreach ($topic in $allData.topics) {
        if ($topic.local_id -like "*test*") {
            try {
                $deleteUrl = "$baseUrl/api/pomodoro/topics/$($topic.server_id)?version=$($topic.version)"
                Write-Host "`nUsuwam temat: $($topic.local_id)" -ForegroundColor Yellow
                Write-Host "  URL: $deleteUrl" -ForegroundColor Gray
                $result = Invoke-RestMethod -Uri $deleteUrl -Method Delete -Headers $headers
                Write-Host "  ✓ Usunięto" -ForegroundColor Green
            } catch {
                Write-Host "  ✗ Błąd: $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
    
    Write-Host "`n✓ Czyszczenie zakończone`n" -ForegroundColor Green
    
} catch {
    Write-Host "✗ Błąd podczas pobierania danych: $($_.Exception.Message)" -ForegroundColor Red
}
