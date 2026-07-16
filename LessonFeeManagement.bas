Attribute VB_Name = "LessonFeeManagement"
Option Explicit

' ピアノ教室 レッスン料管理システム
' 標準モジュールとして取り込んで使用します。

Private Const SHEET_MASTER As String = "生徒マスタ"
Private Const SHEET_CURRENT As String = "当月受付"
Private Const SHEET_HISTORY As String = "入金履歴"
Private Const SHEET_SETTINGS As String = "設定"
Private Const TABLE_STUDENTS As String = "tblStudents"
Private Const TABLE_CURRENT As String = "tblCurrentReception"
Private Const TABLE_PAYMENTS As String = "tblPayments"

Public Sub 当月受付表を作成()
    Dim ws As Worksheet, lo As ListObject, studentTable As ListObject
    Dim studentRow As ListRow, targetRow As ListRow
    Dim targetMonth As Date, studentId As String

    Set ws = ThisWorkbook.Worksheets(SHEET_CURRENT)
    Set lo = ws.ListObjects(TABLE_CURRENT)
    Set studentTable = ThisWorkbook.Worksheets(SHEET_MASTER).ListObjects(TABLE_STUDENTS)
    targetMonth = DateSerial(Year(Date), Month(Date), 1)

    If MsgBox(Format(targetMonth, "yyyy年m月") & "の受付表を作り直しますか？" & vbCrLf & _
              "未反映の入力内容は消去されます。", vbQuestion + vbYesNo) <> vbYes Then Exit Sub

    Application.ScreenUpdating = False
    ws.Range("B2").Value = targetMonth
    lo.DataBodyRange.ClearContents

    For Each studentRow In studentTable.ListRows
        If CStr(studentRow.Range.Cells(1, 9).Value) = "在籍" Then
            studentId = CStr(studentRow.Range.Cells(1, 1).Value)
            If Len(studentId) > 0 Then
                Set targetRow = GetOrAddReceptionRow(lo)
                With targetRow.Range
                    .Cells(1, 1).Value = "未"
                    .Cells(1, 2).Value = "未"
                    .Cells(1, 3).Value = "未"
                    .Cells(1, 4).Value = studentId
                    .Cells(1, 5).Value = studentRow.Range.Cells(1, 2).Value
                    .Cells(1, 6).Value = studentRow.Range.Cells(1, 5).Value
                    .Cells(1, 7).Value = studentRow.Range.Cells(1, 6).Value
                    .Cells(1, 8).FormulaR1C1 = "=SUM(RC[-2]:RC[-1])"
                    .Cells(1, 12).Value = ThisWorkbook.Names("DefaultStaff").RefersToRange.Value
                    .Cells(1, 14).Value = Format(targetMonth, "yyyymm") & "|" & studentId
                End With
            End If
        End If
    Next studentRow

    Application.ScreenUpdating = True
    MsgBox "当月受付表を作成しました。", vbInformation
End Sub

Public Sub 入金履歴へ反映()
    Dim currentTable As ListObject, paymentTable As ListObject
    Dim row As ListRow, newRow As ListRow
    Dim key As String, warningCount As Long, addedCount As Long
    Dim targetMonth As Date

    Set currentTable = ThisWorkbook.Worksheets(SHEET_CURRENT).ListObjects(TABLE_CURRENT)
    Set paymentTable = ThisWorkbook.Worksheets(SHEET_HISTORY).ListObjects(TABLE_PAYMENTS)
    targetMonth = ThisWorkbook.Worksheets(SHEET_CURRENT).Range("B2").Value

    For Each row In currentTable.ListRows
        If Len(CStr(row.Range.Cells(1, 4).Value)) > 0 And CStr(row.Range.Cells(1, 1).Value) = "済" Then
            If CStr(row.Range.Cells(1, 2).Value) <> "済" Then warningCount = warningCount + 1

            If CStr(row.Range.Cells(1, 3).Value) <> "済" Then
                If Len(CStr(row.Range.Cells(1, 9).Value)) = 0 Or Len(CStr(row.Range.Cells(1, 10).Value)) = 0 Then
                    row.Range.Select
                    MsgBox "受取額または受取日が未入力です。" & vbCrLf & _
                           "生徒：" & row.Range.Cells(1, 5).Value, vbExclamation
                    Exit Sub
                End If

                key = Format(targetMonth, "yyyymm") & "|" & CStr(row.Range.Cells(1, 4).Value)
                If PaymentKeyExists(paymentTable, key) Then
                    row.Range.Cells(1, 3).Value = "済"
                Else
                    Set newRow = paymentTable.ListRows.Add
                    With newRow.Range
                        .Cells(1, 1).Value = targetMonth
                        .Cells(1, 2).Value = row.Range.Cells(1, 4).Value
                        .Cells(1, 3).Value = row.Range.Cells(1, 5).Value
                        .Cells(1, 4).Value = row.Range.Cells(1, 8).Value
                        .Cells(1, 5).Value = row.Range.Cells(1, 9).Value
                        .Cells(1, 6).Value = row.Range.Cells(1, 10).Value
                        .Cells(1, 7).Value = row.Range.Cells(1, 11).Value
                        .Cells(1, 8).Value = row.Range.Cells(1, 12).Value
                        .Cells(1, 9).Value = row.Range.Cells(1, 13).Value
                        .Cells(1, 10).Value = key
                        .Cells(1, 11).Value = Now
                    End With
                    row.Range.Cells(1, 3).Value = "済"
                    addedCount = addedCount + 1
                End If
            End If
        End If
    Next row

    If warningCount > 0 Then
        MsgBox addedCount & "件を反映しました。" & vbCrLf & _
               "印鑑未押印が " & warningCount & "件あります。黄色の行を確認してください。", vbExclamation
    Else
        MsgBox addedCount & "件を入金履歴へ反映しました。", vbInformation
    End If
End Sub

Public Sub 印鑑未押印を確認()
    Dim lo As ListObject, row As ListRow, count As Long, names As String
    Set lo = ThisWorkbook.Worksheets(SHEET_CURRENT).ListObjects(TABLE_CURRENT)

    For Each row In lo.ListRows
        If CStr(row.Range.Cells(1, 1).Value) = "済" And CStr(row.Range.Cells(1, 2).Value) <> "済" Then
            count = count + 1
            names = names & vbCrLf & "・" & CStr(row.Range.Cells(1, 5).Value)
        End If
    Next row

    If count = 0 Then
        MsgBox "印鑑未押印はありません。", vbInformation
    Else
        MsgBox "印鑑未押印が " & count & "件あります。" & names, vbExclamation
    End If
End Sub

Public Sub バックアップコピー作成()
    Dim folder As String, fileName As String
    If Len(ThisWorkbook.Path) = 0 Then
        MsgBox "先にブックを保存してください。", vbExclamation
        Exit Sub
    End If

    folder = ThisWorkbook.Path & Application.PathSeparator & "backup"
    If Dir(folder, vbDirectory) = vbNullString Then MkDir folder
    fileName = folder & Application.PathSeparator & _
               "ピアノ教室_レッスン料管理_" & Format(Now, "yyyymmdd_hhnnss") & ".xlsm"
    ThisWorkbook.SaveCopyAs fileName
    MsgBox "バックアップを作成しました。" & vbCrLf & fileName, vbInformation
End Sub

Public Sub 受付済み行の日付補完(ByVal changedCell As Range)
    Dim lo As ListObject, relativeRow As Long
    Set lo = ThisWorkbook.Worksheets(SHEET_CURRENT).ListObjects(TABLE_CURRENT)
    If Intersect(changedCell, lo.ListColumns("受付").DataBodyRange) Is Nothing Then Exit Sub
    If changedCell.CountLarge > 1 Then Exit Sub

    relativeRow = changedCell.Row - lo.DataBodyRange.Row + 1
    If CStr(changedCell.Value) = "済" Then
        If Len(CStr(lo.DataBodyRange.Cells(relativeRow, 10).Value)) = 0 Then
            lo.DataBodyRange.Cells(relativeRow, 10).Value = Date
        End If
    End If
End Sub

Private Function PaymentKeyExists(ByVal lo As ListObject, ByVal key As String) As Boolean
    Dim found As Range
    If lo.DataBodyRange Is Nothing Then Exit Function
    Set found = lo.ListColumns("登録キー").DataBodyRange.Find(What:=key, LookAt:=xlWhole, MatchCase:=False)
    PaymentKeyExists = Not found Is Nothing
End Function

Private Function GetOrAddReceptionRow(ByVal lo As ListObject) As ListRow
    Dim row As ListRow
    For Each row In lo.ListRows
        If Len(CStr(row.Range.Cells(1, 4).Value)) = 0 Then
            Set GetOrAddReceptionRow = row
            Exit Function
        End If
    Next row
    Set GetOrAddReceptionRow = lo.ListRows.Add
End Function

