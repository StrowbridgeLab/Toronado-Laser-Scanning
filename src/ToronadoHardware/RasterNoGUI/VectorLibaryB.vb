Imports System.Runtime.CompilerServices
Imports System.Math
Imports System.IO
Imports System.Text

Module VectorLibary

    Public Function TestVec() As Double()
        Dim TempD As Double()
        ReDim TempD(99)
        For i As Long = 0 To TempD.Length - 1
            TempD(i) = i
        Next
        Return TempD
    End Function
    Public Function TestMatrix() As Double(,)
        Dim TempD As Double(,)
        ReDim TempD(2, 9)
        Dim outC As Double = 0
        For i As Long = 0 To TempD.GetLength(0) - 1
            For j As Long = 0 To TempD.GetLength(1) - 1
                TempD(i, j) = outC
                outC += 1
            Next
        Next
        Return TempD
    End Function
    Public Function LinV(ByVal StartValue As Double, ByVal EndValue As Double, Optional ByVal IncrementValue As Double = 0) As Double()
        Dim TempArray() As Double
        If StartValue = EndValue Then
            MsgBox("LinVector must take two different start/end values")
            TempArray = Nothing
            Return TempArray
        Else
            If IncrementValue = 0 Then
                If EndValue > StartValue Then
                    IncrementValue = 1
                Else
                    IncrementValue = -1
                End If
            End If
            Dim NumValues As Long = 1 + (Abs(EndValue - StartValue) / Abs(IncrementValue))
            ReDim TempArray(NumValues - 1)
            Dim iCount As Long = 0
            Dim Total As Double = StartValue
            Do
                TempArray(iCount) = Total
                Total += IncrementValue
                iCount += 1
            Loop Until iCount = NumValues
            Return TempArray
        End If
    End Function


    <Extension()>
    Public Function Vmean(ByVal inArray As Double()) As Double
        Dim acc As Double = 0
        Dim count As Double = 0
        For i As Long = 0 To inArray.Length - 1
            acc += inArray(i)
            count = count + 1
        Next
        Return acc / count
    End Function

    <Extension()>
    Public Function Vboxcar(ByVal inArray As Double(), boxLength As Long) As Double()
        Dim HalfBoxcar As Long = CLng(boxLength / 2)
        Dim TempD As Double() = inArray.Clone
        Dim StartJ As Long = -1 * HalfBoxcar
        Dim StopJ As Long = (StartJ + boxLength) - 1
        Dim i As Long, j As Long
        Dim Acc As Double
        For i = HalfBoxcar + 1 To inArray.Length - (HalfBoxcar + 1)
            Acc = 0
            For j = StartJ To StopJ
                Acc += inArray(j + i)
            Next
            TempD(i) = Acc / boxLength
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function Vsum(ByVal inArray As Double()) As Double
        Dim acc As Double = 0
        For i As Long = 0 To inArray.Length - 1
            acc += inArray(i)
        Next
        Return acc
    End Function
    <Extension()>
    Public Function Vabssum(ByVal inArray As Double()) As Double
        Dim acc As Double = 0
        For i As Long = 0 To inArray.Length - 1
            acc += Abs(inArray(i))
        Next
        Return acc
    End Function
    <Extension()>
    Public Function Vsine(ByVal inArray As Double()) As Double()
        Dim TempD As Double() = inArray.Clone
        For i As Long = 0 To inArray.Length - 1
            TempD(i) = Sin(inArray(i))
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function Vcos(ByVal inArray As Double()) As Double()
        Dim TempD As Double() = inArray.Clone
        For i As Long = 0 To inArray.Length - 1
            TempD(i) = Cos(inArray(i))
        Next
        Return TempD
    End Function

    <Extension()>
    Public Function VVadd(ByVal inArray As Double(), ByVal newVec As Double()) As Double()
        If inArray.Length <> newVec.Length Then
            MsgBox("InVec and NewVec must be the same length")
            Return Nothing
        End If
        Dim TempD As Double()
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            TempD(i) = inArray(i) + newVec(i)
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function VVdivide(ByVal inArray As Double(), ByVal newVec As Double()) As Double()
        If inArray.Length <> newVec.Length Then
            MsgBox("InVec and NewVec must be the same length")
            Return Nothing
        End If
        Dim TempD As Double()
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            TempD(i) = inArray(i) / newVec(i)
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function VVsub(ByVal inArray As Double(), ByVal newVec As Double()) As Double()
        If inArray.Length <> newVec.Length Then
            MsgBox("InVec and NewVec must be the same length")
            Return Nothing
        End If
        Dim TempD As Double()
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            TempD(i) = inArray(i) - newVec(i)
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function VVmult(ByVal inArray As Double(), ByVal newVec As Double()) As Double()
        Dim TempD As Double()
        If inArray.Length <> newVec.Length Then
            MsgBox("InVec and NewVec must be the same length")
            Return Nothing
        End If
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            TempD(i) = inArray(i) * newVec(i)
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function VVpower(ByVal inArray As Double(), ByVal newVec As Double()) As Double()
        If inArray.Length <> newVec.Length Then
            MsgBox("InVec and NewVec must be the same length")
            Return Nothing
        End If
        Dim TempD As Double()
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            TempD(i) = inArray(i) ^ newVec(i)
        Next
        Return TempD
    End Function

    <Extension()>
    Public Function VSadd(ByVal inArray As Double(), ByVal newScalar As Double) As Double()
        Dim TempD As Double()
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            TempD(i) = inArray(i) + newScalar
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function VSdivide(ByVal inArray As Double(), ByVal newScalar As Double) As Double()
        Dim TempD As Double()
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            TempD(i) = inArray(i) / newScalar
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function VSsub(ByVal inArray As Double(), ByVal newScalar As Double) As Double()
        Dim TempD As Double()
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            TempD(i) = inArray(i) - newScalar
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function VSmult(ByVal inArray As Double(), ByVal newScalar As Double) As Double()
        Dim TempD As Double()
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            TempD(i) = inArray(i) * newScalar
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function VSpower(ByVal inArray As Double(), ByVal newScalar As Double) As Double()
        Dim TempD As Double()
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            TempD(i) = inArray(i) ^ newScalar
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function Vexp(ByVal inArray As Double(), Optional ByVal CoefScalar As Double = 1) As Double()
        Dim TempD As Double()
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            TempD(i) = CoefScalar * Exp(inArray(i))
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function VVexp(ByVal inArray As Double(), ByVal CoefVec As Double()) As Double()
        If inArray.Length <> CoefVec.Length Then
            MsgBox("InputVec and CoefVec must be the same length")
            Return Nothing
        End If
        Dim TempD As Double()
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            TempD(i) = CoefVec(i) * Exp(inArray(i))
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function VVmask(ByVal inArray As Double(), ByVal inMask As Double()) As Double()
        Dim TempD As Double()
        Dim NumHits As Long = 0
        For i As Long = 0 To inMask.Length - 1
            If inMask(i) = 1 Then NumHits += 1
        Next
        If NumHits > 0 Then
            ReDim TempD(NumHits - 1)
            Dim OutIndex As Long = 0
            For i As Long = 0 To inMask.Length - 1
                If inMask(i) = 1 Then
                    TempD(OutIndex) = inArray(i)
                    OutIndex += 1
                End If
            Next
        Else
            TempD = Nothing
        End If
        Return TempD
    End Function

    <Extension()>
    Public Function VmaskGE(ByVal inArray As Double(), ByVal newScalar As Double) As Double()
        Dim NumHits As Long = 0
        For i As Long = 0 To inArray.Length - 1
            If inArray(i) >= newScalar Then NumHits += 1
        Next
        If NumHits > 0 Then
            Dim TempD As Double()
            ReDim TempD(NumHits - 1)
            Dim iCount As Long = 0
            For i = 0 To inArray.Length - 1
                If inArray(i) >= newScalar Then
                    TempD(iCount) = inArray(i)
                    iCount += 1
                End If
            Next
            Return TempD
        Else
            Return Nothing
        End If
    End Function
    <Extension()>
    Public Function VmaskGT(ByVal inArray As Double(), ByVal newScalar As Double) As Double()
        Dim NumHits As Long = 0
        For i As Long = 0 To inArray.Length - 1
            If inArray(i) > newScalar Then NumHits += 1
        Next
        If NumHits > 0 Then
            Dim TempD As Double()
            ReDim TempD(NumHits - 1)
            Dim iCount As Long = 0
            For i = 0 To inArray.Length - 1
                If inArray(i) > newScalar Then
                    TempD(iCount) = inArray(i)
                    iCount += 1
                End If
            Next
            Return TempD
        Else
            Return Nothing
        End If
    End Function
    <Extension()>
    Public Function VmaskLT(ByVal inArray As Double(), ByVal newScalar As Double) As Double()
        Dim NumHits As Long = 0
        For i As Long = 0 To inArray.Length - 1
            If inArray(i) < newScalar Then NumHits += 1
        Next
        If NumHits > 0 Then
            Dim TempD As Double()
            ReDim TempD(NumHits - 1)
            Dim iCount As Long = 0
            For i = 0 To inArray.Length - 1
                If inArray(i) < newScalar Then
                    TempD(iCount) = inArray(i)
                    iCount += 1
                End If
            Next
            Return TempD
        Else
            Return Nothing
        End If
    End Function
    <Extension()>
    Public Function VmaskLE(ByVal inArray As Double(), ByVal newScalar As Double) As Double()
        Dim NumHits As Long = 0
        For i As Long = 0 To inArray.Length - 1
            If inArray(i) <= newScalar Then NumHits += 1
        Next
        If NumHits > 0 Then
            Dim TempD As Double()
            ReDim TempD(NumHits - 1)
            Dim iCount As Long = 0
            For i = 0 To inArray.Length - 1
                If inArray(i) <= newScalar Then
                    TempD(iCount) = inArray(i)
                    iCount += 1
                End If
            Next
            Return TempD
        Else
            Return Nothing
        End If
    End Function
    <Extension()>
    Public Function VmaskEQ(ByVal inArray As Double(), ByVal newScalar As Double) As Double()
        Dim NumHits As Long = 0
        For i As Long = 0 To inArray.Length - 1
            If inArray(i) = newScalar Then NumHits += 1
        Next
        If NumHits > 0 Then
            Dim TempD As Double()
            ReDim TempD(NumHits - 1)
            Dim iCount As Long = 0
            For i = 0 To inArray.Length - 1
                If inArray(i) = newScalar Then
                    TempD(iCount) = inArray(i)
                    iCount += 1
                End If
            Next
            Return TempD
        Else
            Return Nothing
        End If
    End Function
    <Extension()>
    Public Function VmaskNE(ByVal inArray As Double(), ByVal newScalar As Double) As Double()
        Dim NumHits As Long = 0
        For i As Long = 0 To inArray.Length - 1
            If inArray(i) <> newScalar Then NumHits += 1
        Next
        If NumHits > 0 Then
            Dim TempD As Double()
            ReDim TempD(NumHits - 1)
            Dim iCount As Long = 0
            For i = 0 To inArray.Length - 1
                If inArray(i) <> newScalar Then
                    TempD(iCount) = inArray(i)
                    iCount += 1
                End If
            Next
            Return TempD
        Else
            Return Nothing
        End If
    End Function
    <Extension()>
    Public Function VmaskNotNaN(ByVal inArray As Double()) As Double()
        Dim NumHits As Long = 0
        For i As Long = 0 To inArray.Length - 1
            If Not Double.IsNaN(inArray(i)) Then NumHits += 1
        Next
        If NumHits > 0 Then
            Dim TempD As Double()
            ReDim TempD(NumHits - 1)
            Dim iCount As Long = 0
            For i = 0 To inArray.Length - 1
                If Not Double.IsNaN(inArray(i)) Then
                    TempD(iCount) = inArray(i)
                    iCount += 1
                End If
            Next
            Return TempD
        Else
            Return Nothing
        End If
    End Function
    <Extension()>
    Public Function VVsel(ByVal inArray As Double(), ByVal inIndexList As Double()) As Double()
        For i As Long = 0 To inIndexList.Length - 1
            Dim LastPossibleIndex As Long = inArray.Length - 1
            If inIndexList(i) > LastPossibleIndex Then
                MsgBox("InIndexList contains indexes beyond those possible for inputVec")
                Return Nothing
            End If
        Next
        Dim TempD As Double()
        ReDim TempD(inIndexList.Length - 1)
        If inIndexList.Length > 0 Then
            For i As Long = 0 To inIndexList.Length - 1
                TempD(i) = inArray(Fix(inIndexList(i)))
            Next
            Return TempD
        Else
            Return Nothing
        End If
    End Function
    <Extension()>
    Public Function VVsel(ByVal inArray As Int16(), ByVal inIndexList As Double()) As Int16()
        For i As Long = 0 To inIndexList.Length - 1
            Dim LastPossibleIndex As Long = inArray.Length - 1
            If inIndexList(i) > LastPossibleIndex Then
                MsgBox("InIndexList contains indexes beyond those possible for inputVec")
                Return Nothing
            End If
        Next
        Dim TempD As Int16()
        ReDim TempD(inIndexList.Length - 1)
        If inIndexList.Length > 0 Then
            For i As Long = 0 To inIndexList.Length - 1
                TempD(i) = inArray(Fix(inIndexList(i)))
            Next
            Return TempD
        Else
            Return Nothing
        End If
    End Function

    <Extension()>
    Public Function Vsel(ByVal inArray As Double(), ByVal StartValue As Double, ByVal EndValue As Double, Optional ByVal IncrementValue As Double = 0) As Double()
        Return inArray.VVsel(LinV(StartValue, EndValue, IncrementValue))
    End Function
    <Extension()>
    Public Function Vsel(ByVal inArray As Int16(), ByVal StartValue As Double, ByVal EndValue As Double, Optional ByVal IncrementValue As Double = 0) As Int16()
        Return inArray.VVsel(LinV(StartValue, EndValue, IncrementValue))
    End Function
    <Extension()>
    Public Function VreplaceRev(ByVal inMask As Double(), ByVal inArray As Double(), ByVal newValues As Double()) As Double()
        Dim TempD As Double() = inArray.Clone
        If inMask.Length <> newValues.Length Then
            MsgBox("Mask and NewValues vectors must be the same length")
            Return TempD
        End If
        If inMask.Length > 0 Then
            Dim inMaskLong As Long() = Fix(inMask)
            For i As Long = 0 To inMask.Length - 1
                TempD(inMaskLong(i)) = newValues(i)
            Next
        End If
        Return TempD
    End Function
    <Extension()>
    Public Function Vreplace(ByVal inArray As Double(), ByVal inMask As Double(), ByVal newValues As Double()) As Double()
        Dim TempD As Double() = inArray.Clone
        If inMask.Length <> newValues.Length Then
            MsgBox("Mask and NewValues vectors must be the same length")
            Return TempD
        End If
        If inMask.Length > 0 Then
            For i As Long = 0 To inMask.Length - 1
                TempD(Fix(inMask(i))) = newValues(i)
            Next
        End If
        Return TempD
    End Function
    <Extension()>
    Public Function VSreplaceRev(ByVal inMask As Double(), ByVal inArray As Double(), ByVal newValue As Double) As Double()
        Dim TempD As Double() = inArray.Clone
        If inMask.Length > 0 Then
            Dim inMaskLong As Long() = Fix(inMask)
            For i As Long = 0 To inMask.Length - 1
                TempD(inMaskLong(i)) = newValue
            Next
        End If
        Return TempD
    End Function
    <Extension()>
    Public Function VSreplace(ByVal inArray As Double(), ByVal inMask As Double(), ByVal newValue As Double) As Double()
        Dim TempD As Double() = inArray.Clone
        If inMask.Length > 0 Then
            For i As Long = 0 To inMask.Length - 1
                TempD(Fix(inMask(i))) = newValue
            Next
        End If
        Return TempD
    End Function
    <Extension()>
    Public Function VSreplaceScalar(ByVal inArray As Double(), ByVal newValue As Double) As Double()
        Dim TempD As Double() = inArray.Clone
        For i As Long = 0 To inArray.Length - 1
            TempD(i) = newValue
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function Vend(ByVal inArray As Double()) As Double
        Return inArray.Length - 1
    End Function

    <Extension()>
    Public Function Vrepeat(ByVal inArray As Double(), ByVal numRepeats As Double) As Double()
        Dim TempD As Double()
        Dim InVecLength As Long = inArray.Length
        Dim numRepeatsLong As Long = Fix(numRepeats)
        ReDim TempD((numRepeatsLong * InVecLength) - 1)
        For i As Long = 0 To numRepeatsLong - 1
            For j As Long = 0 To InVecLength - 1
                TempD((i * InVecLength) + j) = inArray(j)
            Next
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function Vcat(ByVal inArray As Double(), ByVal newVec As Double()) As Double()
        Dim TempD As Double()
        ReDim TempD((inArray.Length + newVec.Length) - 1)
        Dim iCount As Long = 0
        For i As Long = 0 To inArray.Length - 1
            TempD(iCount) = inArray(i)
            iCount += 1
        Next
        For i As Long = 0 To newVec.Length - 1
            TempD(iCount) = newVec(i)
            iCount += 1
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function VcatBefore(ByVal inArray As Double(), ByVal newVec As Double()) As Double()
        Dim TempD As Double()
        ReDim TempD((inArray.Length + newVec.Length) - 1)
        Dim iCount As Long = 0
        For i As Long = 0 To newVec.Length - 1
            TempD(iCount) = newVec(i)
            iCount += 1
        Next
        For i As Long = 0 To inArray.Length - 1
            TempD(iCount) = inArray(i)
            iCount += 1
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function Vpermute(ByVal inArray As Double(), ByVal IndexMap As Double()) As Double()
        Dim TempD As Double() = inArray.Clone
        If inArray.Length <> IndexMap.Length Then
            MsgBox("IndexMap and InArray lengths must be the same")
            Return Nothing
        Else
            Dim IndexMapLong As Long() = Fix(IndexMap)
            For i As Long = 0 To inArray.Length - 1
                TempD(IndexMapLong(i)) = inArray(i)
            Next
        End If
        Return TempD
    End Function
    <Extension()>
    Public Function Vreverse(ByVal inArray As Double()) As Double()
        Dim TempD As Double() = inArray.Clone
        Dim InArrayLastIndex = inArray.Length - 1
        For i As Long = 0 To InArrayLastIndex
            TempD(InArrayLastIndex - i) = inArray(i)
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function Vreverse(ByVal inArray As Int16()) As Int16()
        Dim TempD As Int16() = inArray.Clone
        Dim InArrayLastIndex = inArray.Length - 1
        For i As Long = 0 To InArrayLastIndex
            TempD(InArrayLastIndex - i) = inArray(i)
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function ToDA1(ByVal inArray() As Double, ByVal FileName As String) As Double()
        Dim TempFileName As String = "R:\Transfer\" + FileName + "_Float_S" + inArray.Length.ToString + ".da1"
        Dim WriteStream As FileStream
        WriteStream = New FileStream(TempFileName, FileMode.Create) ' will overwrite existing data
        Dim WriteBinary As New BinaryWriter(WriteStream)
        For i As Long = 0 To inArray.Length - 1
            WriteBinary.Write(inArray(i))
        Next
        WriteBinary.Close()
        Return inArray
    End Function
    <Extension()>
    Public Function ToDA1(ByVal inArray() As Int16, ByVal FileName As String) As Int16()
        Dim TempFileName As String = "R:\Transfer\" + FileName + "_Int16_S" + inArray.Length.ToString + ".da1"
        Dim WriteStream As FileStream
        WriteStream = New FileStream(TempFileName, FileMode.Create) ' will overwrite existing data
        Dim WriteBinary As New BinaryWriter(WriteStream)
        For i As Long = 0 To inArray.Length - 1
            WriteBinary.Write(inArray(i))
        Next
        WriteBinary.Close()
        Return inArray
    End Function
    <Extension()>
    Public Function ToDA2(ByVal inArray(,) As Int16, ByVal FileName As String) As Int16(,)
        Dim TempFileName As String = "R:\Transfer\" + FileName + +"_Int16_X" + inArray.GetLength(0).ToString + "_Y" + inArray.GetLength(1).ToString + ".da2"
        Dim WriteStream As FileStream
        WriteStream = New FileStream(TempFileName, FileMode.Create) ' will overwrite existing data
        Dim WriteBinary As New BinaryWriter(WriteStream)
        For x As Long = 0 To inArray.GetLength(0) - 1
            For y As Long = 0 To inArray.GetLength(1) - 1
                WriteBinary.Write(inArray(x, y))
            Next
        Next
        WriteBinary.Close()
        Return inArray
    End Function
    <Extension()>
    Public Function ToSavedVector(ByVal inArray() As Double, ByVal FileName As String) As Double()
        Dim TempFileName As String
        Dim WriteStream As FileStream

        If Left(FileName.ToUpper, 4) <> ".DAT" Then
            TempFileName = FileName + ".dat"
        Else
            TempFileName = FileName
        End If
        If TempFileName.Contains("\") Then
            MsgBox("Cannot use file path, static variable must be specified with only a fileName (no path). Append failed.")
            Return inArray
            Exit Function
        End If

        Dim TempFolder As String = "R:\transfer"
        TempFolder = TempFolder.Replace("/", "\")
        If Strings.Right(TempFolder, 1) <> "\" Then
            TempFolder = TempFolder + "\"
        End If
        TempFileName = TempFolder + TempFileName ' to store on hard drive

        WriteStream = New FileStream(TempFileName, FileMode.Create) ' will overwrite existing data
        Dim WriteBinary As New BinaryWriter(WriteStream)
        For i As Long = 0 To inArray.Length - 1
            WriteBinary.Write(inArray(i))
        Next
        WriteBinary.Close()
        Return inArray
    End Function
    <Extension()>
    Public Function VcircShift(ByVal inArray As Double(), ByVal ShiftSize As Double) As Double()
        If ShiftSize >= inArray.Length Then
            MsgBox("ShiftSize parameter cannot be greater than one less than the number of elements in InArray")
            Return Nothing
        End If
        Dim TempD As Double() = inArray.Clone
        Dim NewIndex As Long
        If ShiftSize > 0 Then
            NewIndex = Fix(ShiftSize)
        Else
            NewIndex = inArray.Length + Fix(ShiftSize)
        End If
        For i = 0 To inArray.Length - 1
            TempD(NewIndex) = inArray(i)
            NewIndex += 1
            If NewIndex >= inArray.Length Then NewIndex = 0
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function VboolNot(ByVal inArray As Double()) As Double()
        Dim TempD As Double()
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            If inArray(i) = 1 Then
                TempD(i) = 0
            Else
                TempD(i) = 1
            End If
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function VboolLE(ByVal inArray As Double(), ByVal newScalar As Double) As Double()
        Dim TempD As Double()
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            If inArray(i) <= newScalar Then
                TempD(i) = 1
            Else
                TempD(i) = 0
            End If
        Next
        Return TempD
    End Function

    <Extension()>
    Public Function VboolLT(ByVal inArray As Double(), ByVal newScalar As Double) As Double()
        Dim TempD As Double()
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            If inArray(i) < newScalar Then
                TempD(i) = 1
            Else
                TempD(i) = 0
            End If
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function VboolGE(ByVal inArray As Double(), ByVal newScalar As Double) As Double()
        Dim TempD As Double()
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            If inArray(i) >= newScalar Then
                TempD(i) = 1
            Else
                TempD(i) = 0
            End If
        Next
        Return TempD

    End Function
    <Extension()>
    Public Function VboolGT(ByVal inArray As Double(), ByVal newScalar As Double) As Double()
        Dim TempD As Double()
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            If inArray(i) > newScalar Then
                TempD(i) = 1
            Else
                TempD(i) = 0
            End If
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function VboolEQ(ByVal inArray As Double(), ByVal newScalar As Double) As Double()
        Dim TempD As Double()
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            If inArray(i) = newScalar Then
                TempD(i) = 1
            Else
                TempD(i) = 0
            End If
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function VboolNE(ByVal inArray As Double(), ByVal newScalar As Double) As Double()
        Dim TempD As Double()
        ReDim TempD(inArray.Length - 1)
        For i As Long = 0 To inArray.Length - 1
            If inArray(i) <> newScalar Then
                TempD(i) = 1
            Else
                TempD(i) = 0
            End If
        Next
        Return TempD
    End Function
    <Extension()>
    Public Function VtoMsgBox(ByVal inArray As Double()) As String
        Dim TempStr As String = ""
        For i = 0 To inArray.Length - 1
            TempStr += Format(inArray(i), "F2") + " "
        Next
        MsgBox(TempStr.Trim)
        Return TempStr.Trim
    End Function
    <Extension()>
    Public Function MreplRow(ByVal inMatrix As Double(,), ByVal newVec As Double(), ByVal rowNum As Double) As Double(,)
        Dim TempM As Double(,) = inMatrix.Clone
        If inMatrix.GetLength(1) <> newVec.Length Then
            MsgBox("Column size of inMatrix does not match size of inVec")
            TempM = Nothing
        Else
            Dim rowNumLong As Long = Fix(rowNum)
            For i As Long = 0 To inMatrix.GetLength(1) - 1
                TempM(rowNumLong, i) = newVec(i)
            Next
        End If
        Return TempM
    End Function
    <Extension()>
    Public Function MreplColumn(ByVal inMatrix As Double(,), ByVal newVec As Double(), ByVal colNum As Double) As Double(,)
        Dim TempM As Double(,) = inMatrix.Clone
        If inMatrix.GetLength(0) <> newVec.Length Then
            MsgBox("row size of inMatrix does not match size of inVec")
            TempM = Nothing
        Else
            Dim colNumLong As Long = Fix(colNum)
            For i As Long = 0 To inMatrix.GetLength(1) - 1
                TempM(i, colNumLong) = newVec(i)
            Next
        End If
        Return TempM
    End Function


End Module
