param(
  [string]$Base="http://127.0.0.1:5000"
)

function Post-Json($uri, $headers, $obj) {
  $json = $obj | ConvertTo-Json -Depth 6
  Invoke-RestMethod -Method Post -Uri $uri -Headers $headers `
    -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($json))
}

Write-Host ">>> Salud"
Invoke-RestMethod -Uri "$Base/api/health" | Out-Host

Write-Host ">>> Registrar usuarios"
Invoke-RestMethod -Method Post -Uri "$Base/api/auth/register" -ContentType "application/json" `
  -Body (@{email="docente@demo.com"; password="demo123"; rol="DOCENTE"} | ConvertTo-Json) | Out-Null
Invoke-RestMethod -Method Post -Uri "$Base/api/auth/register" -ContentType "application/json" `
  -Body (@{email="est@demo.com"; password="demo123"; rol="ESTUDIANTE"} | ConvertTo-Json) | Out-Null

Write-Host ">>> Login"
$tokenDoc = (Invoke-RestMethod -Method Post -Uri "$Base/api/auth/login" -ContentType "application/json" `
  -Body (@{email="docente@demo.com"; password="demo123"} | ConvertTo-Json)).access_token
$tokenEst = (Invoke-RestMethod -Method Post -Uri "$Base/api/auth/login" -ContentType "application/json" `
  -Body (@{email="est@demo.com"; password="demo123"} | ConvertTo-Json)).access_token
$hDoc = @{ Authorization = "Bearer $tokenDoc" }
$hEst = @{ Authorization = "Bearer $tokenEst" }

Write-Host ">>> Crear y publicar curso + lección"
$curso = Post-Json "$Base/api/courses/" $hDoc @{ titulo="Python Básico"; descripcion="Curso demo" }
Invoke-RestMethod -Method Post -Uri "$Base/api/courses/$($curso.id)/publish" -Headers $hDoc | Out-Null
Post-Json "$Base/api/courses/$($curso.id)/lessons" $hDoc @{ titulo="Intro"; contenido="Bienvenidos"; orden=1 } | Out-Null

Write-Host ">>> Inscribir estudiante"
Invoke-RestMethod -Method Post -Uri "$Base/api/courses/$($curso.id)/enroll" -Headers $hEst | Out-Host

Write-Host ">>> Crear quiz + pregunta"
$quiz = Post-Json "$Base/api/quizzes/" $hDoc @{ curso_id=$curso.id; titulo="Quiz 1"; tiempo_limite_min=20; intentos_max=2 }
$preg = Post-Json "$Base/api/quizzes/$($quiz.id)/questions" $hDoc @{
  enunciado = "2 + 2 = ?"
  tipo      = "MULTIPLE"
  opciones  = @(
    @{ texto="4"; correcta=$true },
    @{ texto="5"; correcta=$false }
  )
}

Write-Host ">>> Rendir y entregar"
$intento = Invoke-RestMethod -Method Post -Uri "$Base/api/quizzes/$($quiz.id)/attempts" -Headers $hEst
$opCorrecta = ($preg.opciones | Where-Object { $_.correcta -eq $true }).id
$resp = Post-Json "$Base/api/quizzes/attempts/$($intento.intento_id)/submit" $hEst @{ respuestas = @{ "$($preg.id)" = $opCorrecta } }
$resp | Out-Host

Write-Host ">>> OK fin del seed"
