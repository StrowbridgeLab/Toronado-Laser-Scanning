Imports NationalInstruments.DAQmx
Imports System.IO
Imports System.Net.Sockets
Imports Ionic.Zip
Imports System.Math

Public Class BenNI6111
    Private OutTask As Task
    Private InTask As New Task
    Private TasksCreated As Boolean
    Private TasksAreDirty As Boolean
    Friend OutputWaveformsLoaded As Boolean
    Private ZeroGalvosAfterEachScan As Boolean
    Private SampleRate As Double
    Private InRangeList As Double()
    Private OutRange As Double
    Private NumSamples As Double = 0
    Private NumFrames As Long = 0
    Private OuterLoop As Long
    Private mResponseTTLnum As Integer
    Private WaitForExtTrig As Long
    Private PhotometryMode As Boolean
    Private FocusMode As Boolean
    Private FocusModeFirstImage As Boolean
    Private TransferFolder As String ' where to look for scan waveform and where to put final output (should be shared)
    Private TempFolder As String ' where to put the intermediate files prior to zipping (should not be shared)
    Private OutputZipFile As String = ""
    Private NumInputChannels As Long
    Private ReaderU As AnalogUnscaledReader
    Private Writer As AnalogMultiChannelWriter

    Private mDevName As String = ""
    Private mMaxRawValue = 0
    Private mHardwareComputerName = My.Computer.Name

    Private mOriginalXdata As Double() ' added 9 May 2018 for phase dithering
    Private mOriginalYdata As Double()
    Private mPhaseJitter As Boolean = False
    Private mMeanX As Double = 0
    Private mMeanY As Double = 0

    Private devStr As String = ""
    Private decodeStr As String = ""
    Private CmdString As String = ""
    Private deviceType As String = ""
    Private StaticTTLs(7) As Boolean
    Private dataWaveOut(1) As NationalInstruments.AnalogWaveform(Of Double)
    Private ScanType As Long
    Private FullAcquireParameters As Single()
    Private ScanParms As Dictionary(Of String, String)
    Private mCallingInstance As frmRaster
    Private returnIPaddress As System.Net.IPAddress
    Private returnPort As Integer
    Private clientSocket As System.Net.Sockets.TcpClient
    Public Sub New(ByVal CallingInstance As frmRaster, ByVal deviceName As String)
        ' Class Constructor
        '   MsgBox(deviceName)
        mCallingInstance = CallingInstance
        TasksCreated = False
        TasksAreDirty = True
        OutputWaveformsLoaded = False
        SampleRate = 500000
        ReDim InRangeList(3)
        For i As Long = 0 To 1
            InRangeList(i) = 0
        Next
        OutRange = 10
        NumSamples = 999
        OuterLoop = 1200
        TransferFolder = "D:/"
        TempFolder = "R:"
        NumInputChannels = 1
        FocusMode = False
        PhotometryMode = False
        FocusModeFirstImage = True
        WaitForExtTrig = 0
        devStr = deviceName
        For ii = 0 To 7
            StaticTTLs(ii) = 0
            SetDigitalBit(ii, StaticTTLs(ii))
        Next
        ZeroGalvosAfterEachScan = False
        GetCardParameters()

    End Sub
    Public Function SetReturnEndPoint(ByVal IPstring As String, ByVal Portstring As String) As Boolean
        returnIPaddress = System.Net.IPAddress.Parse(IPstring.Trim)
        returnPort = CInt(Portstring)
        Return True
    End Function
    Public Function SetFocusMode(ByVal newValue As Boolean) As Boolean
        If FocusMode <> newValue Then
            FocusMode = newValue
            FocusModeFirstImage = True
        End If
        Return True
    End Function
    Public Function SetWaitForExtTrig(ByVal newValue As Long) As Boolean
        Dim TempL As Long = Math.Abs(newValue)
        If TempL <> WaitForExtTrig Then
            WaitForExtTrig = TempL
            TasksAreDirty = True
        End If
        Return True
    End Function
    Public Function SetPhotometryMode(ByVal newValue As Long) As Boolean
        Dim TempL As Long = Math.Abs(newValue)
        If TempL = 1 Then
            PhotometryMode = True
            SetWaitForExtTrig(1)
            SetReturnEndPoint("0.0.0.0", -1)
            Return True
        Else
            PhotometryMode = False
            SetWaitForExtTrig(0)
            If Not OutTask Is Nothing Then
                OutTask.Dispose()
            End If
            If Not InTask Is Nothing Then
                InTask.Dispose()
            End If
        End If
        Return True
    End Function
    Public Function setMeanXY(newX As Double, newY As Double) As Boolean
        mMeanX = newX
        mMeanY = newY
        Return True
    End Function
    Public Function setResponseTTLnum(ByVal newValue As Integer) As Boolean
        mResponseTTLnum = newValue
        Return True
    End Function
    Public Function SetNumSamples(ByVal NewValue As Double) As Boolean
        If NewValue <> NumSamples Then
            NumSamples = NewValue
            TasksAreDirty = True  ' to trigger reload
        End If
        Return True
    End Function
    Public Function SetTransferFolder(ByVal newFolderName As String) As Boolean
        If My.Computer.FileSystem.DirectoryExists(newFolderName) Then
            TransferFolder = newFolderName
            Return True
        Else
            MsgBox("Requested output folder does not exist: " + newFolderName)
            Return False
        End If
    End Function
    Public Function SetTempFolder(ByVal newName As String) As Boolean
        TempFolder = newName
        Return True
    End Function
    Public Function SetOutputZipFile(ByVal newValue As String) As Boolean
        OutputZipFile = newValue
        Return True
    End Function
    Public Function SetScanParmsDict(ByVal newDict As Dictionary(Of String, String)) As Boolean
        ScanParms = newDict
        Return True
    End Function
    Public Function SetCmdString(ByVal newValue As String) As Boolean

        Return True
    End Function
    Public Function SetOuterLoopFor5ms(ByVal newValue As Long) As Boolean
        OuterLoop = newValue
        Return True
    End Function
    Public Function SetSampleRate(ByVal NewValue As Double) As Boolean
        If NewValue <> SampleRate Then
            SampleRate = NewValue
            TasksAreDirty = True
        End If
        Return True
    End Function
    Public Function SetInputRangeList(ByVal NewValues As Double()) As Boolean
        ' change to take a four element vector; set rangeVolts = 0 to disable acquiring that channel
        InRangeList = NewValues
        Return True
    End Function
    Public Function SetZeroGalvosAfterScan(ByVal NewValue As Long) As Boolean
        If NewValue = 0 Then
            ZeroGalvosAfterEachScan = False
        Else
            ZeroGalvosAfterEachScan = True
        End If
        Return True
    End Function
    Public Function LoadOutputWaveformsRaw(ByRef newX As Double(), ByRef newY As Double()) As Boolean
        NumSamples = newX.Length
        dataWaveOut(0) = NationalInstruments.AnalogWaveform(Of Double).FromArray1D(newX)
        dataWaveOut(1) = NationalInstruments.AnalogWaveform(Of Double).FromArray1D(newY)
        mOriginalXdata = newX
        mOriginalYdata = newY
        Return True
    End Function
    Public Function LoadOutputWaveformsFromVector(ByRef newX As Double(), ByRef newY As Double(), ByVal numFramesIn As Long, ByVal lagPixels As Long) As Boolean
        If numFramesIn < 1 Then
            MsgBox("Requested less than one frame, so resetting to 1 frame")
            NumFrames = 1
        Else
            NumFrames = numFramesIn
        End If
        Dim lastPoint As Double
        Dim extraPoints As Long = lagPixels + 20
        NumSamples = (NumFrames * newX.Length) + extraPoints ' update core parameter in class
        Dim count As Long
        If newX.Length > 0 And newX.Length = newY.Length Then
            Dim finalX As Double()
            ReDim finalX(NumSamples - 1)
            count = 0
            For frame As Long = 0 To NumFrames - 1
                For rawIndex As Long = 0 To newX.Length - 1
                    finalX(count) = newX(rawIndex)
                    count = count + 1
                Next
            Next
            lastPoint = newX(newX.Length - 1)
            For ii As Long = count To newX.Length - 1
                finalX(ii) = lastPoint ' add buffer at end to compensate for ignored lag pixels at beginning
            Next
            dataWaveOut(0) = NationalInstruments.AnalogWaveform(Of Double).FromArray1D(finalX)
            Dim finalY As Double()
            ReDim finalY(NumSamples - 1)
            count = 0
            For frame As Long = 0 To NumFrames - 1
                For rawIndex As Long = 0 To newY.Length - 1
                    finalY(count) = newY(rawIndex)
                    count = count + 1
                Next
            Next
            lastPoint = newY(newY.Length - 1)
            For ii As Long = count To newY.Length - 1
                finalY(ii) = lastPoint ' add buffer at end to compensate for ignored lag pixels at beginning
            Next
            dataWaveOut(1) = NationalInstruments.AnalogWaveform(Of Double).FromArray1D(finalY)
            OutputWaveformsLoaded = True
            Return True
        Else
            MsgBox("Problem with LoadOutputWaveforms in BenNI6111")
            Return False
        End If

    End Function
    Public Function WriteWaveforms() As Boolean
        Writer.WriteWaveform(False, dataWaveOut)
        Return True
    End Function
    Public Function RunNIBoard(ByVal PositionEpisode As Boolean) As Boolean
        Dim RetOkay As Boolean = True
        If PositionEpisode Then
            ' do nothing with shutter if position episode
        Else
            If FocusMode And Not FocusModeFirstImage Or WaitForExtTrig Then
                ' do nothing if already opened shutter
            Else
                SetDigitalBit(0, 1) ' open shutter and wait 5 ms 
                Wait5Millseconds(OuterLoop)
                If FocusMode And FocusModeFirstImage Then
                    FocusModeFirstImage = True ' flag to not bother opening shutter on next focus call
                End If
            End If
        End If
        SetDigitalBit(1, 1) ' TTL line to trigger ePhys DAQ
        OutTask.Start()
        InTask.Start()
        Return RetOkay
    End Function
    Public Function ZeroGalvos()
        SetGalvosStatic(0, 0)
        Return True
    End Function
    Public Function DacsTo2()
        SetGalvosStatic(2, -2)
        Return True
    End Function
    Public Function SetGalvosStatic(ByVal newX As Double, ByVal newY As Double) As Boolean
        Dim ShortTask As Task = Nothing
        Dim ShortTaskWriter As AnalogSingleChannelWriter

        If Not InTask Is Nothing Then InTask.Dispose()
        If Not OutTask Is Nothing Then OutTask.Dispose()
        ShortTask = New Task()
        ShortTask.AOChannels.CreateVoltageChannel(devStr + "/ao0", "", -10, 10, AOVoltageUnits.Volts)
        ShortTaskWriter = New AnalogSingleChannelWriter(ShortTask.Stream)
        ShortTaskWriter.WriteSingleSample(True, newX)
        ShortTask = Nothing

        ShortTask = New Task()
        ShortTask.AOChannels.CreateVoltageChannel(devStr + "/ao1", "", -10, 10, AOVoltageUnits.Volts)
        ShortTaskWriter = New AnalogSingleChannelWriter(ShortTask.Stream)
        ShortTaskWriter.WriteSingleSample(True, newY)
        ShortTask.Stop()
        ShortTask = Nothing

        TasksCreated = False ' to force resetting main NI routines
        Return True
    End Function
    Public Function GetCardParameters() As Boolean
        Dim dev As NationalInstruments.DAQmx.Device = NationalInstruments.DAQmx.DaqSystem.Local.LoadDevice(devStr)
        mDevName = dev.ProductType
        Dim TempStr As String = mDevName.Split("-")(0).ToLower
        If TempStr = "pci" Then
            mMaxRawValue = (2 ^ 11) - 1
        Else
            mMaxRawValue = (2 ^ 15) - 1
        End If

        Return True
    End Function
    Public Function GetCardName() As String
        Dim dev As NationalInstruments.DAQmx.Device = NationalInstruments.DAQmx.DaqSystem.Local.LoadDevice(devStr)
        Return dev.ProductType
    End Function
    Public Function GetMaxValue() As String
        Dim dev As NationalInstruments.DAQmx.Device = NationalInstruments.DAQmx.DaqSystem.Local.LoadDevice(devStr)
        mDevName = dev.ProductType
        Dim TempStr As String = mDevName.Split("-")(0).ToLower
        If TempStr = "pci" Then
            mMaxRawValue = (2 ^ 11) - 1
        Else
            mMaxRawValue = (2 ^ 15) - 1
        End If
        Return mMaxRawValue.ToString
    End Function
    Public Function SetDigitalBit(ByVal BitNum As Long, ByVal BitValue As Long) As Boolean
        Dim DigTask As Task = Nothing
        DigTask = New Task
        DigTask.DOChannels.CreateChannel(devStr + "/port0", "", ChannelLineGrouping.OneChannelForAllLines)
        StaticTTLs(BitNum) = BitValue
        Dim DigWriter As New DigitalSingleChannelWriter(DigTask.Stream)
        DigWriter.WriteSingleSampleMultiLine(True, StaticTTLs)
        DigTask.Dispose()
        Return True
    End Function
    Public Function SetPhaseJitter(ByVal jitterState As Boolean) As Boolean
        mPhaseJitter = jitterState
        Return True
    End Function

    ' private subs below here

    Public Sub CreateTasks()
        If Not OutTask Is Nothing Then
            OutTask.Dispose()
        End If
        If Not InTask Is Nothing Then
            InTask.Dispose()
        End If
        OutTask = New Task("My Out Task")
        InTask = New Task("My In Task")
        OutTask.AOChannels.CreateVoltageChannel(devStr + "/ao0", "", -1.0# * OutRange, OutRange, AOVoltageUnits.Volts)
        OutTask.AOChannels.CreateVoltageChannel(devStr + "/ao1", "", -1.0# * OutRange, OutRange, AOVoltageUnits.Volts)
        OutTask.Timing.ConfigureSampleClock("", SampleRate, SampleClockActiveEdge.Rising, SampleQuantityMode.FiniteSamples, NumSamples)
        For adcNum As Long = 0 To 3
            If InRangeList(adcNum) > 0 Then
                Try
                    ' Best mode for PCI-6111 type boards
                    InTask.AIChannels.CreateVoltageChannel(devStr + "/ai" + adcNum.ToString, "", AITerminalConfiguration.Pseudodifferential, -1.0# * InRangeList(adcNum), InRangeList(adcNum), AIVoltageUnits.Volts)
                Catch ex As Exception
                    '  Best mode for PCIe-6251 type boards
                    InTask.AIChannels.CreateVoltageChannel(devStr + "/ai" + adcNum.ToString, "", AITerminalConfiguration.Rse, -1.0# * InRangeList(adcNum), InRangeList(adcNum), AIVoltageUnits.Volts)
                End Try
            End If
        Next

        ReaderU = New AnalogUnscaledReader(InTask.Stream)
        InTask.Timing.ConfigureSampleClock("", SampleRate, SampleClockActiveEdge.Rising, SampleQuantityMode.FiniteSamples, NumSamples)
        OutTask.Triggers.StartTrigger.ConfigureDigitalEdgeTrigger("/" + devStr + "/ai/StartTrigger", DigitalEdgeStartTriggerEdge.Rising)
        If WaitForExtTrig <> 0 Then
            InTask.Triggers.StartTrigger.ConfigureAnalogEdgeTrigger("PFI0", AnalogEdgeStartTriggerSlope.Rising, 0.5)
        End If
        AddHandler InTask.Done, AddressOf AnalogInFinished
        Writer = New AnalogMultiChannelWriter(OutTask.Stream)
        InTask.SynchronizeCallbacks = True
        OutTask.SynchronizeCallbacks = True
        TasksCreated = True
        TasksAreDirty = False

    End Sub

    Private Function Wait5Millseconds(ByVal OuterLoopValue As Long) As Boolean
        Dim TempD As Double
        Dim j As Long, k As Long
        For j = 0 To OuterLoopValue
            For k = 0 To 1000
                TempD = 2325451.23232# / 235556.323423#
                TempD = 2325451.23232# / 235556.323423#
                TempD = 2325451.23232# / 235556.323423#
            Next
        Next
        Application.DoEvents()
        Return True
    End Function
    Private Sub DisposeOfTasks()
        ' MsgBox("Inside dispose")
        InTask.Dispose()
        If Not OutTask Is Nothing Then OutTask.Dispose()
        TasksCreated = False
    End Sub
    Private Sub AnalogInFinished()
        If Not FocusMode Then
            SetDigitalBit(0, 0) ' close shutter
        End If
        SetDigitalBit(1, 0) ' turn off DAQ trig signal

        Dim ChanAdata As Int16() = Nothing
        Dim ChanBdata As Int16() = Nothing
        Dim UnscaledData(,) As Int16

        UnscaledData = ReaderU.ReadInt16(NumSamples)
        Dim a1 As Long = UnscaledData.GetUpperBound(0)
        Dim a2 As Long = UnscaledData.GetUpperBound(1)
        InTask.Stop()
        OutTask.Stop()

        If returnPort = -1 Then
            If mPhaseJitter Then
                Dim offsetPoints As Long = CLng(Rnd() * 500) ' add 0.5 ms jitter
                LoadOutputWaveformsRaw(addPhaseDelay(mOriginalXdata, offsetPoints), addPhaseDelay(mOriginalYdata, offsetPoints))
                WriteWaveforms()
            End If
            InTask.Start() ' to mimick retriggerable startTrigger
            OutTask.Start()
            If PhotometryMode Then
                Dim TempStr As String = "Photometry done."
                If mCallingInstance.InvokeRequired Then
                    mCallingInstance.Invoke(Sub()
                                                mCallingInstance.Text = TempStr
                                            End Sub)
                Else
                    mCallingInstance.Text = TempStr
                End If
            End If
            Return ' do not save file or respond to Toronado program
        End If

        If My.Computer.FileSystem.FileExists(OutputZipFile) Then
            My.Computer.FileSystem.DeleteFile(OutputZipFile)
        End If

        Dim newFileRoot As String
        Dim adcName As String
        Dim unscaledIndex As Long = 0
        Dim ResponseStr As String = ""
        Using zip As ZipFile = New ZipFile
            For Each fName In My.Computer.FileSystem.GetFiles(TempFolder)
                zip.AddFile(fName, "")
            Next
            For chan As Long = 0 To 3
                If InRangeList(chan) > 0 Then
                    newFileRoot = "ADC" + Chr(48 + chan) + "_ImageRaw_int16.bin"
                    adcName = TempFolder + "/" + newFileRoot
                    Using WriteStream = New FileStream(adcName, FileMode.Create) ' will overwrite existing data
                        Using WriteBinary As New BinaryWriter(WriteStream)
                            For ii As Long = 0 To a2
                                WriteBinary.Write(UnscaledData(unscaledIndex, ii))
                            Next
                        End Using
                    End Using
                    zip.AddFile(adcName, "")
                    unscaledIndex = unscaledIndex + 1
                End If
            Next ' chan
            zip.Save(OutputZipFile)
        End Using
        Application.DoEvents()
        ' now send zip file containg acquired binary data and desc text files back to first computer
        Dim ipLocalEndPoint As New System.Net.IPEndPoint(returnIPaddress, returnPort)
        Dim Socket As New Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp)
        Try
            Socket.Connect(ipLocalEndPoint)
            Socket.SendFile(OutputZipFile)
            Socket.Shutdown(SocketShutdown.Both)
            mCallingInstance.ClearTitle()
        Catch ex As Exception
            mCallingInstance.ClearTitle("Error - Return socket refused.")
        End Try
        Socket.Close()

        '     frmRaster.mLJ.OutputTTL(mResponseTTLnum, 1) ' bring TTL line high for 25 ms to indicate acq is finished
        For Each FileName In Directory.GetFiles(TempFolder) ' clear all contents in TempFolder but leave folder
            My.Computer.FileSystem.DeleteFile(FileName)
        Next

    End Sub

    Private Function addDelayToVector(ByRef inVector As Double(), ByVal numDelayPoints As Long) As Double()
        Dim tempArray As Double()
        ReDim tempArray(inVector.Length)
        Dim Count As Long = 0
        For ii = 0 To inVector.Length - 1
            If ii < numDelayPoints Then
                tempArray(ii) = inVector(numDelayPoints)
            Else
                tempArray(ii) = inVector(Count)
                Count = Count + 1
            End If
        Next
        tempArray(tempArray.Length - 1) = inVector(numDelayPoints) ' make sure the galvos always stay near the correct point
        Return tempArray
    End Function

    Private Function addPhaseDelay(ByRef inVector As Double(), ByVal numDelayPoints As Long) As Double()
        Dim tempArray As Double()
        ReDim tempArray(inVector.Length)
        Dim meanValue As Double
        For ii As Long = 0 To inVector.Length - 1
            meanValue = meanValue + inVector(ii)
        Next ii
        meanValue = meanValue / inVector.Length

        For ii As Long = 0 To inVector.Length - 1
            If ii < inVector.Length - numDelayPoints Then
                tempArray(ii) = inVector(ii + numDelayPoints)
            Else
                tempArray(ii) = meanValue
            End If
        Next ii

        Return tempArray
    End Function

    Protected Overrides Sub Finalize()
        Try
            '  If Not Form1.NoNIBoard Then DisposeOfTasks()
            MyBase.Finalize()
        Catch
        End Try
    End Sub
End Class
