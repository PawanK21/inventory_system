# Test script for Inventory Management System API

Write-Host "🧪 Inventory Management System - API Test Suite" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://localhost:8000"
$headers = @{"Content-Type" = "application/json"}

# Function to make API calls
function Invoke-ApiCall {
    param([string]$Method, [string]$Endpoint, [object]$Body)
    $url = "$baseUrl$Endpoint"
    try {
        if ($Body) {
            $response = Invoke-WebRequest -Uri $url -Method $Method -Headers $headers -Body ($Body | ConvertTo-Json) -UseBasicParsing -ErrorAction Stop
        } else {
            $response = Invoke-WebRequest -Uri $url -Method $Method -Headers $headers -UseBasicParsing -ErrorAction Stop
        }
        return @{
            Status = $response.StatusCode
            Content = $response.Content | ConvertFrom-Json
        }
    } catch {
        return @{
            Status = "Error"
            Content = $_.Exception.Message
        }
    }
}

# Test 1: Get all items
Write-Host "Test 1: Get All Items" -ForegroundColor Yellow
$result = Invoke-ApiCall -Method GET -Endpoint "/api/items"
Write-Host "Status: $($result.Status)" -ForegroundColor Green
Write-Host "Items Count: $($result.Content.Count)`n"

# Test 2: Get stock summary
Write-Host "Test 2: Get Stock Summary for Item" -ForegroundColor Yellow
$result = Invoke-ApiCall -Method GET -Endpoint "/api/inventory/summary/1"
Write-Host "Status: $($result.Status)" -ForegroundColor Green
Write-Host "OnHand: $($result.Content.onHand), Available: $($result.Content.available)`n"

# Test 3: Get all lots
Write-Host "Test 3: Get All Lots" -ForegroundColor Yellow
$result = Invoke-ApiCall -Method GET -Endpoint "/api/lots"
Write-Host "Status: $($result.Status)" -ForegroundColor Green
Write-Host "Lots Count: $($result.Content.Count)`n"

# Test 4: Get all reservations
Write-Host "Test 4: Get All Reservations" -ForegroundColor Yellow
$result = Invoke-ApiCall -Method GET -Endpoint "/api/reservations"
Write-Host "Status: $($result.Status)" -ForegroundColor Green
Write-Host "Reservations Count: $($result.Content.Count)`n"

# Test 5: Get dashboard stats
Write-Host "Test 5: Get Dashboard Statistics" -ForegroundColor Yellow
$result = Invoke-ApiCall -Method GET -Endpoint "/api/stats"
Write-Host "Status: $($result.Status)" -ForegroundColor Green
Write-Host "Total Items: $($result.Content.totalItems)"
Write-Host "Total Lots: $($result.Content.totalLots)"
Write-Host "Approved Lots: $($result.Content.approvedLots)"
Write-Host "Active Reservations: $($result.Content.activeReservations)`n"

# Test 6: Get ledger entries
Write-Host "Test 6: Get Ledger Entries" -ForegroundColor Yellow
$result = Invoke-ApiCall -Method GET -Endpoint "/api/ledger"
Write-Host "Status: $($result.Status)" -ForegroundColor Green
Write-Host "Ledger Entries Count: $($result.Content.Count)`n"

Write-Host "✅ All tests completed!" -ForegroundColor Green
