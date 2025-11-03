# Test Script dla Pomodoro API Endpoints
# Autor: AI Assistant
# Data: 2025-11-02

Write-Host "`n╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   POMODORO API ENDPOINTS - TEST SUITE     ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Załaduj token
$token = Get-Content "token.txt" -ErrorAction Stop
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

$baseUrl = "http://127.0.0.1:8000"
$testsPassed = 0
$testsFailed = 0

# ============================================================================
# TEST 1: POST /api/pomodoro/topics - Tworzenie tematu
# ============================================================================
Write-Host "TEST 1: POST /api/pomodoro/topics - Tworzenie nowego tematu" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor DarkGray

$topicData = @{
    local_id = "topic_test_001"
    name = "Nauka Python"
    color = "#FF5733"
    icon = "🐍"
    description = "Sesje nauki programowania w Python"
    total_sessions = 0
    total_work_time = 0
    total_break_time = 0
    is_favorite = $true
    sort_order = 1
    version = 1
    last_modified = "2025-11-02T17:00:00Z"
} | ConvertTo-Json

try {
    $topicResponse = Invoke-RestMethod -Uri "$baseUrl/api/pomodoro/topics" -Method Post -Headers $headers -Body $topicData
    Write-Host "✓ PASSED - Temat utworzony pomyślnie" -ForegroundColor Green
    Write-Host "  Server ID: $($topicResponse.server_id)" -ForegroundColor Gray
    Write-Host "  Name: $($topicResponse.name)" -ForegroundColor Gray
    Write-Host "  Version: $($topicResponse.version)" -ForegroundColor Gray
    $topicServerId = $topicResponse.server_id
    $topicServerId | Out-File -FilePath "topic_id.txt" -NoNewline
    $testsPassed++
} catch {
    Write-Host "✗ FAILED - $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails) {
        Write-Host ($_.ErrorDetails.Message | ConvertFrom-Json | ConvertTo-Json -Depth 5) -ForegroundColor DarkRed
    }
    $testsFailed++
}

Start-Sleep -Seconds 1

# ============================================================================
# TEST 2: GET /api/pomodoro/all?type=topic - Pobieranie tematów
# ============================================================================
Write-Host "`nTEST 2: GET /api/pomodoro/all?type=topic - Pobieranie tematów" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor DarkGray

try {
    $allTopics = Invoke-RestMethod -Uri "$baseUrl/api/pomodoro/all?type=topic" -Method Get -Headers $headers
    Write-Host "✓ PASSED - Pobrano tematy" -ForegroundColor Green
    Write-Host "  Liczba tematów: $($allTopics.topics.Count)" -ForegroundColor Gray
    if ($allTopics.topics.Count -gt 0) {
        Write-Host "  Pierwszy temat: $($allTopics.topics[0].name)" -ForegroundColor Gray
    }
    $testsPassed++
} catch {
    Write-Host "✗ FAILED - $($_.Exception.Message)" -ForegroundColor Red
    $testsFailed++
}

Start-Sleep -Seconds 1

# ============================================================================
# TEST 3: POST /api/pomodoro/topics - Aktualizacja tematu (ten sam local_id)
# ============================================================================
Write-Host "`nTEST 3: POST /api/pomodoro/topics - Aktualizacja istniejącego tematu" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor DarkGray

$topicUpdateData = @{
    local_id = "topic_test_001"
    name = "Nauka Python - Zaawansowane"
    color = "#FF5733"
    icon = "🐍"
    description = "Sesje nauki zaawansowanego Python"
    total_sessions = 5
    total_work_time = 125
    total_break_time = 25
    is_favorite = $true
    sort_order = 1
    version = 2
    last_modified = "2025-11-02T18:00:00Z"
} | ConvertTo-Json

try {
    $topicUpdateResponse = Invoke-RestMethod -Uri "$baseUrl/api/pomodoro/topics" -Method Post -Headers $headers -Body $topicUpdateData
    Write-Host "✓ PASSED - Temat zaktualizowany" -ForegroundColor Green
    Write-Host "  Name: $($topicUpdateResponse.name)" -ForegroundColor Gray
    Write-Host "  Version: $($topicUpdateResponse.version)" -ForegroundColor Gray
    Write-Host "  Total sessions: $($topicUpdateResponse.total_sessions)" -ForegroundColor Gray
    $testsPassed++
} catch {
    Write-Host "✗ FAILED - $($_.Exception.Message)" -ForegroundColor Red
    $testsFailed++
}

Start-Sleep -Seconds 1

# ============================================================================
# TEST 4: POST /api/pomodoro/topics - Konflikt wersji (409)
# ============================================================================
Write-Host "`nTEST 4: POST /api/pomodoro/topics - Test konfliktu wersji (oczekiwany 409)" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor DarkGray

$topicConflictData = @{
    local_id = "topic_test_001"
    name = "To nie powinno się zapisać"
    color = "#FF5733"
    icon = "🐍"
    version = 1  # Stara wersja - konflikt!
    last_modified = "2025-11-02T16:00:00Z"
} | ConvertTo-Json

try {
    $conflictResponse = Invoke-RestMethod -Uri "$baseUrl/api/pomodoro/topics" -Method Post -Headers $headers -Body $topicConflictData
    Write-Host "✗ FAILED - Powinien zwrócić 409 Conflict!" -ForegroundColor Red
    $testsFailed++
} catch {
    if ($_.Exception.Response.StatusCode -eq 409) {
        Write-Host "✓ PASSED - Konflikt wersji wykryty poprawnie (409)" -ForegroundColor Green
        $errorDetail = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Host "  Server version: $($errorDetail.detail.server_version)" -ForegroundColor Gray
        Write-Host "  Local version: $($errorDetail.detail.local_version)" -ForegroundColor Gray
        $testsPassed++
    } else {
        Write-Host "✗ FAILED - Błędny kod statusu: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
        $testsFailed++
    }
}

Start-Sleep -Seconds 1

# ============================================================================
# TEST 5: POST /api/pomodoro/sessions - Tworzenie sesji
# ============================================================================
Write-Host "`nTEST 5: POST /api/pomodoro/sessions - Tworzenie sesji Pomodoro" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor DarkGray

$sessionData = @{
    local_id = "session_test_001"
    topic_id = $topicServerId
    session_date = "2025-11-02"
    started_at = "2025-11-02T10:00:00Z"
    ended_at = "2025-11-02T10:25:00Z"
    work_duration = 25
    short_break_duration = 5
    actual_work_time = 25
    actual_break_time = 0
    session_type = "work"
    status = "completed"
    pomodoro_count = 1
    notes = "Dobra sesja nauki Python"
    tags = @("python", "nauka", "fokus")
    productivity_rating = 4
    version = 1
    last_modified = "2025-11-02T10:30:00Z"
} | ConvertTo-Json

try {
    $sessionResponse = Invoke-RestMethod -Uri "$baseUrl/api/pomodoro/sessions" -Method Post -Headers $headers -Body $sessionData
    Write-Host "✓ PASSED - Sesja utworzona" -ForegroundColor Green
    Write-Host "  Server ID: $($sessionResponse.server_id)" -ForegroundColor Gray
    Write-Host "  Session type: $($sessionResponse.session_type)" -ForegroundColor Gray
    Write-Host "  Status: $($sessionResponse.status)" -ForegroundColor Gray
    $sessionServerId = $sessionResponse.server_id
    $sessionServerId | Out-File -FilePath "session_id.txt" -NoNewline
    $testsPassed++
} catch {
    Write-Host "✗ FAILED - $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails) {
        Write-Host ($_.ErrorDetails.Message | ConvertFrom-Json | ConvertTo-Json -Depth 5) -ForegroundColor DarkRed
    }
    $testsFailed++
}

Start-Sleep -Seconds 1

# ============================================================================
# TEST 6: GET /api/pomodoro/all - Pobieranie wszystkiego
# ============================================================================
Write-Host "`nTEST 6: GET /api/pomodoro/all - Pobieranie tematów i sesji" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor DarkGray

try {
    $allData = Invoke-RestMethod -Uri "$baseUrl/api/pomodoro/all" -Method Get -Headers $headers
    Write-Host "✓ PASSED - Pobrano wszystkie dane" -ForegroundColor Green
    Write-Host "  Liczba tematów: $($allData.topics.Count)" -ForegroundColor Gray
    Write-Host "  Liczba sesji: $($allData.sessions.Count)" -ForegroundColor Gray
    $testsPassed++
} catch {
    Write-Host "✗ FAILED - $($_.Exception.Message)" -ForegroundColor Red
    $testsFailed++
}

Start-Sleep -Seconds 1

# ============================================================================
# TEST 7: DELETE /api/pomodoro/sessions/{id} - Usuwanie sesji
# ============================================================================
Write-Host "`nTEST 7: DELETE /api/pomodoro/sessions/{id} - Soft delete sesji" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor DarkGray

try {
    $deleteSessionResponse = Invoke-RestMethod -Uri "$baseUrl/api/pomodoro/sessions/$sessionServerId`?version=1" -Method Delete -Headers $headers
    Write-Host "✓ PASSED - Sesja usunięta (soft delete)" -ForegroundColor Green
    Write-Host "  Message: $($deleteSessionResponse.message)" -ForegroundColor Gray
    $testsPassed++
} catch {
    Write-Host "✗ FAILED - $($_.Exception.Message)" -ForegroundColor Red
    $testsFailed++
}

Start-Sleep -Seconds 1

# ============================================================================
# TEST 8: DELETE /api/pomodoro/topics/{id} - Usuwanie tematu
# ============================================================================
Write-Host "`nTEST 8: DELETE /api/pomodoro/topics/{id} - Soft delete tematu" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor DarkGray

try {
    $deleteTopicResponse = Invoke-RestMethod -Uri "$baseUrl/api/pomodoro/topics/$topicServerId`?version=3" -Method Delete -Headers $headers
    Write-Host "✓ PASSED - Temat usunięty (soft delete)" -ForegroundColor Green
    Write-Host "  Message: $($deleteTopicResponse.message)" -ForegroundColor Gray
    $testsPassed++
} catch {
    Write-Host "✗ FAILED - $($_.Exception.Message)" -ForegroundColor Red
    $testsFailed++
}

# ============================================================================
# PODSUMOWANIE
# ============================================================================
Write-Host "`n╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║           TEST SUMMARY                     ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝`n" -ForegroundColor Cyan

$totalTests = $testsPassed + $testsFailed
$successRate = [math]::Round(($testsPassed / $totalTests) * 100, 2)

Write-Host "Total Tests:   $totalTests" -ForegroundColor White
Write-Host "Passed:        " -NoNewline
Write-Host $testsPassed -ForegroundColor Green
Write-Host "Failed:        " -NoNewline
Write-Host $testsFailed -ForegroundColor Red
Write-Host "Success Rate:  $successRate%" -ForegroundColor $(if ($successRate -eq 100) { "Green" } elseif ($successRate -ge 75) { "Yellow" } else { "Red" })

if ($testsPassed -eq $totalTests) {
    Write-Host "`n✓✓✓ ALL TESTS PASSED! ✓✓✓" -ForegroundColor Green
} else {
    Write-Host "`n⚠ Some tests failed. Review the output above." -ForegroundColor Yellow
}

Write-Host ""
