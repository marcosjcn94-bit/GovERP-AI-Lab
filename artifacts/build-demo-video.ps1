$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$asset = Join-Path $root '.runtime\gov-erp-video'
$outDir = Join-Path $root 'artifacts'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$pptxPath = Join-Path $outDir 'gov-erp-ai-lab-demo.pptx'
$mp4Path = Join-Path $outDir 'gov-erp-ai-lab-demo.mp4'
function Rgb([int]$r,[int]$g,[int]$b) { return $r + ($g -shl 8) + ($b -shl 16) }
$navy = Rgb 13 32 45; $green = Rgb 8 126 100; $mint = Rgb 221 241 234; $ink = Rgb 24 43 54; $muted = Rgb 88 109 118; $paper = Rgb 247 250 248; $white = Rgb 255 255 255; $red = Rgb 164 51 61; $paleRed = Rgb 249 231 232
function Set-Bg($slide,[int]$color) { $slide.FollowMasterBackground = $false; $slide.Background.Fill.Solid(); $slide.Background.Fill.ForeColor.RGB = $color }
function Add-Rect($slide,[double]$x,[double]$y,[double]$w,[double]$h,[int]$color,[bool]$rounded=$false,[double]$transparency=0) {
  $kind = 1; if ($rounded) { $kind = 5 }
  $s = $slide.Shapes.AddShape($kind,$x,$y,$w,$h); $s.Fill.Solid(); $s.Fill.ForeColor.RGB=$color; $s.Fill.Transparency=$transparency; $s.Line.Visible=0; return $s
}
function Add-Text($slide,[string]$text,[double]$x,[double]$y,[double]$w,[double]$h,[double]$size,[int]$color,[bool]$bold=$false) {
  $s = $slide.Shapes.AddTextbox(1,$x,$y,$w,$h); $s.TextFrame.WordWrap=-1; $s.TextFrame.MarginLeft=0; $s.TextFrame.MarginRight=0; $s.TextFrame.MarginTop=0; $s.TextFrame.MarginBottom=0; $s.TextFrame.TextRange.Text=$text; $s.TextFrame.TextRange.Font.Name='Aptos'; $s.TextFrame.TextRange.Font.Size=$size; $s.TextFrame.TextRange.Font.Bold=[int]$bold; $s.TextFrame.TextRange.Font.Color.RGB=$color; $s.Line.Visible=0; return $s
}
function Add-Header($slide,[string]$title,[string]$section) { Add-Text $slide $section.ToUpper() 44 24 850 20 11 $green $true | Out-Null; Add-Text $slide $title 44 48 870 42 26 $ink $true | Out-Null }
function Add-ScreenSlide($presentation,[string]$image,[string]$section,[string]$caption,[int]$number) {
  $slide=$presentation.Slides.Add($number,12); Set-Bg $slide $navy
  $path=Join-Path $asset $image; if(-not(Test-Path $path)){throw "Captura ausente: $path"}
  $slide.Shapes.AddPicture($path,$false,$true,0,0,960,540) | Out-Null
  Add-Rect $slide 0 426 960 114 $navy $false 0.08 | Out-Null
  Add-Rect $slide 38 445 5 65 $green | Out-Null
  Add-Text $slide $section.ToUpper() 59 442 850 20 10 $mint $true | Out-Null
  Add-Text $slide $caption 59 464 858 57 16 $white $false | Out-Null
  Add-Text $slide ([string]$number + ' / 8') 889 16 45 18 9 $white $false | Out-Null
  return $slide
}
$ppt = $null; $pres = $null
try {
  $ppt = New-Object -ComObject PowerPoint.Application
  $ppt.DisplayAlerts = 1
  $pres = $ppt.Presentations.Add($true)
  $pres.PageSetup.SlideWidth = 960; $pres.PageSetup.SlideHeight = 540
  $s=$pres.Slides.Add(1,12); Set-Bg $s $navy
  Add-Rect $s 68 82 8 368 $green | Out-Null
  Add-Text $s 'GOVERP AI LAB' 100 96 780 24 13 $mint $true | Out-Null
  Add-Text $s 'Serviços municipais\ncom evidência e revisão' 100 150 790 125 36 $white $true | Out-Null
  Add-Text $s 'Demonstração local · Paraná · dados sintéticos' 100 304 770 28 19 $mint $false | Out-Null
  Add-Rect $s 100 372 310 46 $green $true | Out-Null
  Add-Text $s 'RELATÓRIO  ·  AUDITORIA  ·  FONTES' 116 385 280 22 11 $white $true | Out-Null
  Add-Text $s '1 / 8' 889 16 45 18 9 $white $false | Out-Null

  Add-ScreenSlide $pres '01-overview.png' '01 · Visão geral' 'Sessão demonstrativa em Curitiba. O assistente conecta perguntas aos dados do município; cálculos continuam no backend e a tela deixa explícito que a base é sintética.' 2 | Out-Null
  Add-ScreenSlide $pres '04-report-result.png' '02 · Relatório verificável' 'A tabela compara despesas pagas e mostra a memória numérica. Nesta execução real, o Qwen não concluiu; o app preservou os cálculos e exibiu o fallback determinístico.' 3 | Out-Null
  Add-ScreenSlide $pres '03-audit.png' '03 · Controle interno' 'Regras determinísticas apontam possíveis duplicidades para revisão humana. Um achado é um pedido de análise, não uma conclusão de fraude.' 4 | Out-Null
  Add-ScreenSlide $pres '02-ranking.png' '04 · Competitividade' 'A aplicação exibe notas e posições publicadas pelo CLP 2026, com proveniência. Ela não recalcula o ranking; municípios fora do recorte aparecem indisponíveis.' 5 | Out-Null

  $s=$pres.Slides.Add(6,12); Set-Bg $s $paper; Add-Header $s 'O que muda de 10 para 100 municípios' '05 · Escala de dados'
  $cards=@(@{x=44;label='MUNICÍPIOS';value='10 → 100';detail='10× identidades'},@{x=270;label='LANÇAMENTOS';value='148k → 200k';detail='1,35× linhas'},@{x=496;label='DOCUMENTOS';value='1.120 → 3.000';detail='2,68× documentos'},@{x=722;label='BANCO';value='55,36 → 74,62';detail='MiB · +35%'})
  foreach($c in $cards){Add-Rect $s $c.x 142 194 158 $white $true | Out-Null;Add-Text $s $c.label ($c.x+16) 160 162 16 10 $green $true | Out-Null;Add-Text $s $c.value ($c.x+16) 196 164 35 22 $ink $true | Out-Null;Add-Text $s $c.detail ($c.x+16) 244 164 20 12 $muted $false | Out-Null}
  Add-Rect $s 44 330 872 94 $mint $true | Out-Null;Add-Text $s '34,85 s para gerar a carga de 100 municípios' 64 347 830 30 21 $ink $true | Out-Null;Add-Text $s 'Amostra local: 200 mil linhas e 3 mil documentos. Não representa concorrência nem carga de produção.' 64 383 820 28 12 $muted $false | Out-Null;Add-Text $s '6 / 8' 889 16 45 18 9 $muted $false | Out-Null

  $s=$pres.Slides.Add(7,12); Set-Bg $s $paper; Add-Header $s 'Qwen3:4b local — avaliação exploratória reprovada' '06 · Qualidade e latência'
  $metrics=@(@{x=54;value='67,2 s';label='até o fallback da API'},@{x=362;value='0 / 3';label='explicações aceitas estritamente'},@{x=670;value='1 / 3';label='comparações numéricas corretas'})
  foreach($m in $metrics){Add-Rect $s $m.x 144 262 124 $white $true | Out-Null;Add-Text $s $m.value ($m.x+18) 159 226 48 31 $red $true | Out-Null;Add-Text $s $m.label ($m.x+18) 211 226 38 13 $muted $false | Out-Null}
  Add-Rect $s 54 294 878 114 $paleRed $true | Out-Null;Add-Text $s 'Falha crítica observada' 74 311 820 26 18 $red $true | Out-Null;Add-Text $s 'O modelo obedeceu uma instrução injetada e inventou uma lei vigente e um canal. Ollama rodou em CPU; p95 ainda não medido.' 74 345 820 50 14 $ink $false | Out-Null;Add-Text $s 'Cálculos, permissões e decisões permanecem determinísticos. Não usar o Qwen para afirmar vigência ou orientar ação administrativa.' 54 437 860 54 14 $ink $true | Out-Null;Add-Text $s '7 / 8' 889 16 45 18 9 $muted $false | Out-Null

  $s=$pres.Slides.Add(8,12); Set-Bg $s $navy; Add-Rect $s 68 80 8 378 $green | Out-Null;Add-Text $s 'GOVERP AI LAB' 100 93 780 24 12 $mint $true | Out-Null;Add-Text $s 'A evidência dirige a decisão.\nA pessoa revisa o que exige julgamento.' 100 140 790 112 31 $white $true | Out-Null;Add-Text $s 'Próximos passos' 100 290 350 24 14 $mint $true | Out-Null;Add-Text $s 'Corrigir saída/truncamento · repetir holdout · validar segurança e latência · revisão humana' 100 326 790 72 17 $white $false | Out-Null;Add-Text $s 'Demonstração local · dados sintéticos · sem publicação externa' 100 432 770 24 12 $mint $false | Out-Null;Add-Text $s '8 / 8' 889 16 45 18 9 $white $false | Out-Null

  if(Test-Path $pptxPath){Remove-Item -LiteralPath $pptxPath -Force}
  if(Test-Path $mp4Path){Remove-Item -LiteralPath $mp4Path -Force}
  $pres.SaveAs($pptxPath,24)
  Write-Output "PPTX salvo: $pptxPath"
  $pres.CreateVideo($mp4Path,$false,14,1080,30,85)
  $deadline=(Get-Date).AddMinutes(8); $last=-1
  do { Start-Sleep -Seconds 2; $status=$pres.CreateVideoStatus; if($status -ne $last){Write-Output "Status de exportação PowerPoint: $status";$last=$status}; if((Get-Date) -gt $deadline){throw 'Exportação excedeu 8 minutos.'} } while($status -eq 1)
  if($status -ne 3){throw "Exportação terminou com status inesperado: $status"}
  $pres.Save()
  Write-Output "MP4 salvo: $mp4Path"
} finally { if($pres){$pres.Close()}; if($ppt){$ppt.Quit()} }
