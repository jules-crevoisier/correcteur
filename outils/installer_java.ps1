# Telecharge un Java portable dans le dossier "jre" de l'application.
# Evite a l'utilisateur d'installer Java lui-meme : indispensable pour une
# application lancee au demarrage, ou un echec passerait inapercu.

$ErrorActionPreference = "Stop"
$racine = Split-Path -Parent $PSScriptRoot
$cible  = Join-Path $racine "jre"

if (Test-Path (Join-Path $cible "bin\java.exe")) {
    Write-Host "Java portable deja present."
    exit 0
}

$architecture = if ([Environment]::Is64BitOperatingSystem) { "x64" } else { "x86" }
$url = "https://api.adoptium.net/v3/binary/latest/17/ga/windows/$architecture/jre/hotspot/normal/eclipse"
$archive = Join-Path $env:TEMP "correcteur-jre.zip"
$extraction = Join-Path $env:TEMP "correcteur-jre"

Write-Host "Telechargement de Java 17 ($architecture, ~45 Mo)..."
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $url -OutFile $archive -UseBasicParsing

Write-Host "Extraction..."
if (Test-Path $extraction) { Remove-Item $extraction -Recurse -Force }
Expand-Archive -Path $archive -DestinationPath $extraction -Force

# L'archive contient un unique dossier « jdk-17.x.y+z-jre » : on le remonte.
$interieur = Get-ChildItem $extraction -Directory | Select-Object -First 1
if (-not $interieur) { throw "Archive Java inattendue : aucun dossier trouve." }

if (Test-Path $cible) { Remove-Item $cible -Recurse -Force }
Move-Item $interieur.FullName $cible

Remove-Item $archive -Force -ErrorAction SilentlyContinue
Remove-Item $extraction -Recurse -Force -ErrorAction SilentlyContinue

if (-not (Test-Path (Join-Path $cible "bin\java.exe"))) {
    throw "Installation de Java incomplete."
}
Write-Host "Java portable installe dans $cible"
