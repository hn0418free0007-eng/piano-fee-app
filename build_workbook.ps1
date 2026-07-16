$ErrorActionPreference = 'Stop'

$outputPath = Join-Path $PSScriptRoot 'ピアノ教室_レッスン料管理.xlsx'
$excel = $null
$workbook = $null

function Set-HeaderStyle($range) {
    $range.Font.Bold = $true
    $range.Font.Color = 0xFFFFFF
    $range.Interior.Color = 0x78542F
    $range.HorizontalAlignment = -4108
    $range.VerticalAlignment = -4108
    $range.WrapText = $true
}

function Set-TitleStyle($range) {
    $range.Font.Name = 'Yu Gothic UI'
    $range.Font.Size = 18
    $range.Font.Bold = $true
    $range.Font.Color = 0x5C3B1E
}

function Add-ListValidation($range, $formula) {
    $range.Validation.Delete()
    $range.Validation.Add(3, 1, 1, $formula)
    $range.Validation.IgnoreBlank = $true
    $range.Validation.InCellDropdown = $true
    $range.Validation.ShowError = $true
    $range.Validation.ErrorTitle = '入力内容を確認してください'
    $range.Validation.ErrorMessage = '一覧から選択してください。'
}

try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.ScreenUpdating = $false
    $excel.EnableEvents = $false
    $workbook = $excel.Workbooks.Add()
    Write-Output 'Excel started'

    while ($workbook.Worksheets.Count -lt 5) { [void]$workbook.Worksheets.Add() }
    $names = @('生徒マスタ', '当月受付', '入金履歴', 'ダッシュボード', '設定')
    for ($i = 1; $i -le 5; $i++) { $workbook.Worksheets.Item($i).Name = $names[$i - 1] }
    while ($workbook.Worksheets.Count -gt 5) { $workbook.Worksheets.Item($workbook.Worksheets.Count).Delete() }

    $master = $workbook.Worksheets.Item('生徒マスタ')
    $current = $workbook.Worksheets.Item('当月受付')
    $history = $workbook.Worksheets.Item('入金履歴')
    $dash = $workbook.Worksheets.Item('ダッシュボード')
    $settings = $workbook.Worksheets.Item('設定')

    foreach ($ws in @($master, $current, $history, $dash, $settings)) {
        $ws.Cells.Font.Name = 'Yu Gothic UI'
        $ws.Cells.Font.Size = 10
        $ws.Application.ActiveWindow.DisplayGridlines = $false
    }

    # 設定
    $settings.Range('A1:D1').Merge()
    $settings.Range('A1').Value2 = '設定・選択肢'
    Set-TitleStyle $settings.Range('A1')
    $settings.Range('A3:D3').Value2 = @('受付状態', '支払方法', '在籍状況', '教室')
    Set-HeaderStyle $settings.Range('A3:D3')
    $settings.Range('A4:A5').Value2 = @('未', '済')
    $settings.Range('B4:B8').Value2 = @('現金', '振込', '口座振替', 'PayPay', 'その他')
    $settings.Range('C4:C6').Value2 = @('在籍', '休会', '退会')
    $settings.Range('D4:D6').Value2 = @('瑞江', '竹ノ塚', 'その他')
    $settings.Range('F3:G3').Value2 = @('設定項目', '値')
    Set-HeaderStyle $settings.Range('F3:G3')
    $settings.Range('F4').Value2 = '既定担当者'
    $settings.Range('G4').Value2 = '先生'
    $settings.Range('F5').Value2 = '当月受付最大行数'
    $settings.Range('G5').Value2 = 100
    [void]$workbook.Names.Add('StatusList', "='設定'!`$A`$4:`$A`$5")
    [void]$workbook.Names.Add('PaymentList', "='設定'!`$B`$4:`$B`$8")
    [void]$workbook.Names.Add('EnrollmentList', "='設定'!`$C`$4:`$C`$6")
    [void]$workbook.Names.Add('SchoolList', "='設定'!`$D`$4:`$D`$6")
    [void]$workbook.Names.Add('DefaultStaff', "='設定'!`$G`$4")
    $settings.Columns('A:G').AutoFit() | Out-Null
    $settings.Columns('F').ColumnWidth = 24
    $settings.Range('A10:G12').Merge()
    $settings.Range('A10').Value2 = "このシートの選択肢を変更すると、各入力欄のプルダウンにも反映されます。`n行の追加や選択肢変更は、設計書を確認してから行ってください。"
    $settings.Range('A10').WrapText = $true
    $settings.Range('A10').Interior.Color = 0xEAF2F8
    Write-Output 'Settings completed'

    # 生徒マスタ
    $master.Range('A1:J1').Merge()
    $master.Range('A1').Value2 = '生徒マスタ'
    Set-TitleStyle $master.Range('A1')
    $master.Range('A2:J2').Merge()
    $master.Range('A2').Value2 = '生徒の基本情報を1人1行で管理します。生徒IDは重複しない値にしてください。'
    $master.Range('A4:J4').Value2 = @('生徒ID','氏名','教室','学年','月謝','発表会費','入会日','退会日','在籍状況','備考')
    Set-HeaderStyle $master.Range('A4:J4')
    $students = @(
        @('S001','青空 ひなた','瑞江','小学1年',7000,12000,[datetime]'2025-04-01',$null,'在籍','サンプルデータ'),
        @('S002','若葉 みどり','瑞江','小学3年',7500,12000,[datetime]'2024-09-01',$null,'在籍','サンプルデータ'),
        @('S003','星野 かなで','竹ノ塚','小学5年',8000,15000,[datetime]'2023-04-01',$null,'在籍','サンプルデータ'),
        @('S004','音羽 りずむ','竹ノ塚','中学1年',9000,15000,[datetime]'2022-06-01',$null,'在籍','サンプルデータ'),
        @('S005','虹川 つばさ','瑞江','年長',6500,12000,[datetime]'2026-04-01',$null,'在籍','サンプルデータ')
    )
    for ($r=0; $r -lt $students.Count; $r++) {
        for ($c=0; $c -lt 10; $c++) {
            $value = $students[$r][$c]
            if ($value -is [datetime]) { $master.Cells.Item(5+$r,1+$c).Value2 = [double]$value.ToOADate() }
            elseif ($value -is [int]) { $master.Cells.Item(5+$r,1+$c).Value2 = [double]$value }
            elseif ($null -eq $value) { $master.Cells.Item(5+$r,1+$c).ClearContents() }
            else { $master.Cells.Item(5+$r,1+$c).Value2 = [string]$value }
        }
    }
    $master.Range('E5:F200').NumberFormatLocal = '#,##0"円"'
    $master.Range('G5:H200').NumberFormat = 'yyyy-mm-dd'
    Add-ListValidation $master.Range('C5:C200') '=SchoolList'
    Add-ListValidation $master.Range('I5:I200') '=EnrollmentList'
    $masterTable = $master.ListObjects.Add(1, $master.Range('A4:J9'), $null, 1)
    $masterTable.Name = 'tblStudents'
    $masterTable.TableStyle = 'TableStyleMedium2'
    $master.Columns('A:J').AutoFit() | Out-Null
    $master.Columns('B').ColumnWidth = 18
    $master.Columns('J').ColumnWidth = 24
    $master.Activate(); $excel.ActiveWindow.FreezePanes = $false; $excel.ActiveWindow.SplitRow = 4; $excel.ActiveWindow.FreezePanes = $true
    Write-Output 'Student master completed'

    # 当月受付
    $current.Range('A1:N1').Merge()
    $current.Range('A1').Value2 = '当月受付'
    Set-TitleStyle $current.Range('A1')
    $current.Range('A2').Value2 = '対象年月'
    $current.Range('B2').Formula = '=DATE(YEAR(TODAY()),MONTH(TODAY()),1)'
    $current.Range('B2').NumberFormat = 'yyyy"年"m"月"'
    $current.Range('D2:N2').Merge()
    $current.Range('D2').Value2 = '日常操作：封筒受領 → 受付「済」→ 受領印 → 印鑑「済」→ 履歴反映後に売上反映「済」'
    $current.Range('D2').Interior.Color = 0xEAF2F8
    $current.Range('A5:N5').Value2 = @('受付','印鑑','売上反映','生徒ID','氏名','月謝','発表会費','当月請求額','実際の受取額','受取日','支払方法','担当者','備考','登録キー')
    Set-HeaderStyle $current.Range('A5:N5')
    for ($r=6; $r -le 105; $r++) {
        $current.Cells.Item($r,1).Value2 = '未'
        $current.Cells.Item($r,2).Value2 = '未'
        $current.Cells.Item($r,3).Value2 = '未'
        if ($r -le 10) { $current.Cells.Item($r,4).Value2 = ('S{0:D3}' -f ($r-5)) }
        $current.Cells.Item($r,5).Formula = "=IFERROR(VLOOKUP(D$r,'生徒マスタ'!`$A`$5:`$J`$200,2,FALSE),`"`" )"
        $current.Cells.Item($r,6).Formula = "=IFERROR(VLOOKUP(D$r,'生徒マスタ'!`$A`$5:`$J`$200,5,FALSE),`"`" )"
        $current.Cells.Item($r,7).Formula = "=IFERROR(VLOOKUP(D$r,'生徒マスタ'!`$A`$5:`$J`$200,6,FALSE),`"`" )"
        $current.Cells.Item($r,8).Formula = "=IF(D$r=`"`",`"`",SUM(F$r:G$r))"
        $current.Cells.Item($r,12).Formula = '=IF(D'+$r+'="","",DefaultStaff)'
        $current.Cells.Item($r,14).Formula = '=IF(OR($B$2="",D'+$r+'=""),"",TEXT($B$2,"yyyymm")&"|"&D'+$r+')'
    }
    # サンプル操作状態
    $current.Range('A6:C6').Value2 = @('済','済','済'); $current.Range('I6').Value2 = 19000; $current.Range('J6').Value2 = [datetime]::Today; $current.Range('K6').Value2='現金'
    $current.Range('A7:C7').Value2 = @('済','未','未'); $current.Range('I7').Value2 = 19500; $current.Range('J7').Value2 = [datetime]::Today; $current.Range('K7').Value2='振込'
    $current.Range('A8:C8').Value2 = @('済','済','未'); $current.Range('I8').Value2 = 23000; $current.Range('J8').Value2 = [datetime]::Today; $current.Range('K8').Value2='PayPay'
    $current.Range('A9:C9').Value2 = @('済','済','未'); $current.Range('K9').Value2='現金'
    Add-ListValidation $current.Range('A6:C105') '=StatusList'
    Add-ListValidation $current.Range('K6:K105') '=PaymentList'
    $current.Range('F6:I105').NumberFormatLocal = '#,##0"円"'
    $current.Range('J6:J105').NumberFormat = 'yyyy-mm-dd'
    $current.Range('N:N').EntireColumn.Hidden = $true
    $currentTable = $current.ListObjects.Add(1, $current.Range('A5:N105'), $null, 1)
    $currentTable.Name = 'tblCurrentReception'
    $currentTable.TableStyle = 'TableStyleMedium2'

    # 条件付き書式（赤を最優先）
    $dataRange = $current.Range('A6:M105')
    $dataRange.FormatConditions.Delete()
    $fc = $dataRange.FormatConditions.Add(2, $null, '=AND($D6<>"",$A6="済",OR($I6="",$J6=""))')
    $fc.Interior.Color = 0xC7C7FF; $fc.Font.Color = 0x0000C0; $fc.StopIfTrue = $true
    $fc = $dataRange.FormatConditions.Add(2, $null, '=AND($D6<>"",$C6="済")')
    $fc.Interior.Color = 0xF0D9B5; $fc.StopIfTrue = $true
    $fc = $dataRange.FormatConditions.Add(2, $null, '=AND($D6<>"",$A6="済",$B6="済",$C6="未")')
    $fc.Interior.Color = 0xC6EFCE; $fc.StopIfTrue = $true
    $fc = $dataRange.FormatConditions.Add(2, $null, '=AND($D6<>"",$A6="済",$B6="未")')
    $fc.Interior.Color = 0x99FFFF; $fc.StopIfTrue = $true
    $current.Columns('A:N').AutoFit() | Out-Null
    $current.Columns('E').ColumnWidth = 18; $current.Columns('M').ColumnWidth = 24
    $current.Range('A6:C105').HorizontalAlignment = -4108
    $current.Activate(); $excel.ActiveWindow.FreezePanes = $false; $excel.ActiveWindow.SplitRow = 5; $excel.ActiveWindow.SplitColumn = 4; $excel.ActiveWindow.FreezePanes = $true
    Write-Output 'Current reception completed'

    # 入金履歴
    $history.Range('A1:K1').Merge()
    $history.Range('A1').Value2 = '入金履歴'
    Set-TitleStyle $history.Range('A1')
    $history.Range('A2:K2').Merge()
    $history.Range('A2').Value2 = '1件1行の追記型データです。登録キー（年月|生徒ID）で二重登録を防止します。'
    $history.Range('A4:K4').Value2 = @('年月','生徒ID','氏名','請求額','受取額','受取日','支払方法','担当者','備考','登録キー','登録日時')
    Set-HeaderStyle $history.Range('A4:K4')
    $history.Range('A5:K5').Value2 = @([datetime]::new((Get-Date).Year,(Get-Date).Month,1),'S001','青空 ひなた',19000,19000,[datetime]::Today,'現金','先生','サンプル：反映済',(''+(Get-Date -Format yyyyMM)+'|S001'),[datetime]::Now)
    $history.Range('A5:A5000').NumberFormat = 'yyyy-mm'
    $history.Range('D5:E5000').NumberFormatLocal = '#,##0"円"'
    $history.Range('F5:F5000').NumberFormat = 'yyyy-mm-dd'
    $history.Range('K5:K5000').NumberFormat = 'yyyy-mm-dd hh:mm'
    Add-ListValidation $history.Range('G5:G5000') '=PaymentList'
    $historyTable = $history.ListObjects.Add(1, $history.Range('A4:K5'), $null, 1)
    $historyTable.Name = 'tblPayments'
    $historyTable.TableStyle = 'TableStyleMedium2'
    $history.Columns('A:K').AutoFit() | Out-Null
    $history.Columns('C').ColumnWidth = 18; $history.Columns('I').ColumnWidth = 25
    $history.Activate(); $excel.ActiveWindow.FreezePanes = $false; $excel.ActiveWindow.SplitRow = 4; $excel.ActiveWindow.FreezePanes = $true
    Write-Output 'Payment history completed'

    # ダッシュボード
    $dash.Range('A1:H1').Merge(); $dash.Range('A1').Value2 = 'ダッシュボード'; Set-TitleStyle $dash.Range('A1')
    $dash.Range('A2').Value2 = '対象年月'; $dash.Range('B2').Formula = "='当月受付'!B2"; $dash.Range('B2').NumberFormat='yyyy"年"m"月"'
    $labels = @('当月請求総額','当月入金額','未入金額','未受付人数','印鑑未押印人数','売上未反映人数')
    for($i=0;$i -lt $labels.Count;$i++){ $dash.Cells.Item(4+$i,1).Value2=$labels[$i] }
    $dash.Range('A4:A9').Font.Bold=$true; $dash.Range('A4:A9').Interior.Color=0xE8D9C5
    $dash.Range('B4').Formula="=SUM('当月受付'!H6:H105)"
    $dash.Range('B5').Formula="=SUM('当月受付'!I6:I105)"
    $dash.Range('B6').Formula='=MAX(0,B4-B5)'
    $dash.Range('B7').Formula="=COUNTIFS('当月受付'!D6:D105,`"<>`",'当月受付'!A6:A105,`"未`")"
    $dash.Range('B8').Formula="=COUNTIFS('当月受付'!D6:D105,`"<>`",'当月受付'!A6:A105,`"済`",'当月受付'!B6:B105,`"未`")"
    $dash.Range('B9').Formula="=COUNTIFS('当月受付'!D6:D105,`"<>`",'当月受付'!A6:A105,`"済`",'当月受付'!C6:C105,`"未`")"
    $dash.Range('B4:B6').NumberFormatLocal='#,##0"円"'; $dash.Range('B7:B9').NumberFormat='0"人"'
    $dash.Range('B4:B9').Font.Size=16; $dash.Range('B4:B9').Font.Bold=$true
    $dash.Range('D3:H3').Merge(); $dash.Range('D3').Value2='未入金生徒一覧'; Set-HeaderStyle $dash.Range('D3:H3')
    $dash.Range('D4:H4').Value2=@('生徒ID','氏名','請求額','受取額','不足額'); Set-HeaderStyle $dash.Range('D4:H4')
    for($r=5;$r -le 104;$r++){
        $src=$r+1
        $dash.Cells.Item($r,4).Formula="=IF(AND('当月受付'!D$src<>`"`",'当月受付'!H$src>'当月受付'!I$src),'当月受付'!D$src,`"`")"
        $dash.Cells.Item($r,5).Formula="=IF(D$r=`"`",`"`",'当月受付'!E$src)"
        $dash.Cells.Item($r,6).Formula="=IF(D$r=`"`",`"`",'当月受付'!H$src)"
        $dash.Cells.Item($r,7).Formula="=IF(D$r=`"`",`"`",'当月受付'!I$src)"
        $dash.Cells.Item($r,8).Formula="=IF(D$r=`"`",`"`",F$r-G$r)"
    }
    $dash.Range('F5:H105').NumberFormatLocal='#,##0"円"'
    $dash.Range('A12:C12').Merge(); $dash.Range('A12').Value2='年間売上集計'; Set-HeaderStyle $dash.Range('A12:C12')
    $dash.Range('A13').Value2='集計年'; $dash.Range('B13').Formula='=YEAR(B2)'
    $dash.Range('A14:C14').Value2=@('月','入金額','件数'); Set-HeaderStyle $dash.Range('A14:C14')
    for($m=1;$m -le 12;$m++){
        $row=14+$m; $dash.Cells.Item($row,1).Value2=[double]$m
        $dash.Cells.Item($row,2).Formula="=SUMIFS('入金履歴'!`$E`$5:`$E`$5000,'入金履歴'!`$A`$5:`$A`$5000,`">=`"&DATE(`$B`$13,A$row,1),'入金履歴'!`$A`$5:`$A`$5000,`"<`"&EDATE(DATE(`$B`$13,A$row,1),1))"
        $dash.Cells.Item($row,3).Formula="=COUNTIFS('入金履歴'!`$A`$5:`$A`$5000,`">=`"&DATE(`$B`$13,A$row,1),'入金履歴'!`$A`$5:`$A`$5000,`"<`"&EDATE(DATE(`$B`$13,A$row,1),1))"
    }
    $dash.Range('B15:B26').NumberFormatLocal='#,##0"円"'; $dash.Range('C15:C26').NumberFormat='0"件"'
    $dash.Columns('A:H').ColumnWidth=16; $dash.Columns('B').ColumnWidth=18; $dash.Columns('E').ColumnWidth=18
    $dash.Range('A4:B9').Borders.LineStyle=1; $dash.Range('D4:H18').Borders.LineStyle=1
    $dash.Activate(); $excel.ActiveWindow.FreezePanes=$false; $excel.ActiveWindow.SplitRow=2; $excel.ActiveWindow.FreezePanes=$true
    Write-Output 'Dashboard completed'

    # 表示
    $dash.Activate()
    $excel.ActiveWindow.Zoom = 90
    if(Test-Path $outputPath){ Remove-Item -LiteralPath $outputPath -Force }
    $workbook.SaveAs($outputPath, 51)
    $workbook.Close($true)
    $excel.Quit()
    Write-Output "Created: $outputPath"
}
finally {
    if ($workbook) { try { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($workbook) } catch {} }
    if ($excel) { try { $excel.Quit() } catch {}; try { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel) } catch {} }
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
