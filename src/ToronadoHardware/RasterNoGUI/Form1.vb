Imports System.Collections.Generic
Imports System.Windows.Forms
Imports Microsoft.VisualBasic
Imports System.IO.Ports
Imports System.Threading
Imports System.Runtime.InteropServices
Imports System.IO
Imports Microsoft.Win32
Imports System.Diagnostics
Imports Ionic.Zip

Public Class frmRaster
    Const HWND_BROADCAST As Integer = &HFFFF
    Const SC_MONITORPOWER As Integer = &HF170
    Const WM_SYSCOMMAND As Short = &H112S
    Const GWL_EXSTYLE As Integer = -20
    Const WS_EX_TOOLWINDOW As Integer = &H80
    Const WS_EX_APPWINDOW As Integer = &H40000
    <DllImport("user32.dll")> _
    Private Shared Function SendMessage(ByVal hWnd As Integer, ByVal hMsg As Integer, ByVal wParam As Integer, ByVal lParam As Integer) As Integer
    End Function
    <DllImport("user32.dll")> _
    Public Shared Function SetWindowLong(ByVal window As IntPtr, ByVal index As Integer, ByVal value As Integer) As Integer
    End Function
    <DllImport("user32.dll")> _
    Public Shared Function GetWindowLong(ByVal window As IntPtr, ByVal index As Integer) As Integer
    End Function

    Private mVersion As Single = 1.21 ' last update 11 May 2018 BWS
    Private mNI As BenNI6111
    Private mOutputZipFile As String
    Private INIFileName As String
    Private mSystemINI As Dictionary(Of String, String) ' hardware settings
    Private WorkerThread As Thread
    Private W As benTCPlistener
    Private SW As New System.Diagnostics.Stopwatch
    Private mRedPreAmp As clsSerialPreAmpControl
    Private mGreenPreAmp As clsSerialPreAmpControl
    Private UseSerialPreAmpControl As Boolean = True
    Private SerialPreAmpInPhotometryMode = True
    Private CardModelString As String
    Private CardMaxValueString As String

    Public Sub runRasterHeadless()
        Dim TempStr As String
        Using inZip As ZipFile = ZipFile.Read(mSystemINI("tempInputFile"))
            If My.Computer.FileSystem.DirectoryExists(mSystemINI("tempExtractFolder")) Then
                My.Computer.FileSystem.DeleteDirectory(mSystemINI("tempExtractFolder"), FileIO.DeleteDirectoryOption.DeleteAllContents)
            End If
            inZip.ExtractAll(mSystemINI("tempExtractFolder"))
        End Using
        My.Computer.FileSystem.DeleteFile(mSystemINI("tempInputFile"))

        Dim mCmdDict As Dictionary(Of String, String) = ReadIniFile(mSystemINI("tempExtractFolder") + "/" + mSystemINI("cmdFileName"))
        Select Case mCmdDict("currentcommand").ToLower().Trim()
            Case "closeshutter"
                mNI.SetDigitalBit(0, 0) ' close shutter
                mNI.SetFocusMode(False)
            Case "disarmphotometry"
                mNI.SetPhotometryMode(0)
                If UseSerialPreAmpControl Then
                    mRedPreAmp.SetPhotometryMode(0)
                    mGreenPreAmp.SetPhotometryMode(0)
                    SerialPreAmpInPhotometryMode = False
                End If
                TempStr = "photometry disarmed"
                If Me.InvokeRequired Then
                    Me.Invoke(Sub()
                                  Me.Text = TempStr
                              End Sub)
                Else
                    Me.Text = TempStr
                End If
            Case "doloadphotometry"
                ' code for Arming photometry system
                Dim mImageParms As Dictionary(Of String, String) = ReadIniFile(mSystemINI("tempExtractFolder") +
                                                                                   "/" + mCmdDict("imagedesc"))
                ' setup empty folder for output files that will get zipped together
                Dim mSaveFolder As String = mSystemINI("tempSaveFolder")
                If My.Computer.FileSystem.DirectoryExists(mSaveFolder) Then
                    My.Computer.FileSystem.DeleteDirectory(mSaveFolder, FileIO.DeleteDirectoryOption.DeleteAllContents)
                End If
                My.Computer.FileSystem.CopyFile(mSystemINI("tempExtractFolder") + "/" + mSystemINI("cmdFileName"),
                                                mSaveFolder + "/" + mSystemINI("cmdFileName"), True)
                My.Computer.FileSystem.CopyFile(INIFileName, mSaveFolder + "/hardwareSettings.txt", True)

                Dim NewRanges As Double()
                ReDim NewRanges(3)
                NewRanges(0) = 10.0
                NewRanges(1) = 10.0

                mNI.SetInputRangeList(NewRanges)
                mNI.SetSampleRate(1000000.0 / CDbl(mImageParms("pixelus"))) ' uS to MHz
                Dim xData As Double() = readBinaryVector(mSystemINI("tempExtractFolder") + "/" + mImageParms("scanpointsx"))
                Dim yData As Double() = readBinaryVector(mSystemINI("tempExtractFolder") + "/" + mImageParms("scanpointsy"))
                Dim xMean As Double = 0
                Dim yMean As Double = 0
                For ii As Long = 0 To xData.Length - 1
                    xMean = xMean + xData(ii)
                    yMean = yMean + yData(ii)
                Next
                xMean = xMean / xData.Length
                yMean = yMean / yData.Length
                xData(xData.Length - 1) = xMean
                yData(yData.Length - 1) = yMean
                mNI.LoadOutputWaveformsRaw(xData, yData)
                mNI.SetPhotometryMode(1)
                If UseSerialPreAmpControl Then
                    mRedPreAmp.SetPhotometryMode(1)
                    mGreenPreAmp.SetPhotometryMode(1)
                    SerialPreAmpInPhotometryMode = True
                End If
                mNI.SetGalvosStatic(xMean, yMean)
                mNI.setMeanXY(xMean, yMean)
                mNI.CreateTasks()
                mNI.WriteWaveforms()
                mNI.RunNIBoard(False) ' False means PMTs and True means return position

                TempStr = "photometry armed and waiting for trig"
                If Me.InvokeRequired Then
                    Me.Invoke(Sub()
                                  Me.Text = TempStr
                              End Sub)
                Else
                    Me.Text = TempStr
                End If
            Case "dotestphotometry"
                Dim mImageParms As Dictionary(Of String, String) = ReadIniFile(mSystemINI("tempExtractFolder") +
                                                                                   "/" + mCmdDict("imagedesc"))
                Dim NewRanges As Double()
                ReDim NewRanges(3)
                NewRanges(0) = 10.0
                NewRanges(1) = 10.0
                mNI.SetInputRangeList(NewRanges)
                mNI.SetSampleRate(1000000.0 / CDbl(mImageParms("pixelus"))) ' uS to MHz
                Dim xData As Double() = readBinaryVector(mSystemINI("tempExtractFolder") + "/" + mImageParms("scanpointsx"))
                Dim yData As Double() = readBinaryVector(mSystemINI("tempExtractFolder") + "/" + mImageParms("scanpointsy"))
                mNI.LoadOutputWaveformsRaw(xData, yData)
                mNI.SetReturnEndPoint(mCmdDict("returnipaddress"), CInt(mCmdDict("returnport")))
                mNI.SetTempFolder(mSystemINI("tempSaveFolder"))
                mNI.SetOutputZipFile(mSystemINI("tempOutputFile"))
                mNI.SetWaitForExtTrig(0)
                TempStr = "test photometry spot"
                If Me.InvokeRequired Then
                    Me.Invoke(Sub()
                                  Me.Text = TempStr
                              End Sub)
                Else
                    Me.Text = TempStr
                End If
                mNI.CreateTasks()
                mNI.WriteWaveforms()
                mNI.RunNIBoard(False) ' False means PMTs and True means return position

            Case "doscan"
                SW.Reset()
                SW.Start()
                If SerialPreAmpInPhotometryMode Then
                    ' In case Toronado stopped while ToronadoHardware was still in photometry mode
                    mRedPreAmp.SetPhotometryMode(0)
                    mGreenPreAmp.SetPhotometryMode(0)
                    SerialPreAmpInPhotometryMode = False
                End If
                ' setup empty folder for output files that will get zipped together
                Dim mSaveFolder As String = mSystemINI("tempSaveFolder")
                If My.Computer.FileSystem.DirectoryExists(mSaveFolder) Then
                    My.Computer.FileSystem.DeleteDirectory(mSaveFolder, FileIO.DeleteDirectoryOption.DeleteAllContents)
                End If
                My.Computer.FileSystem.CopyFile(mSystemINI("tempExtractFolder") + "/" + mSystemINI("cmdFileName"),
                                                mSaveFolder + "/" + mSystemINI("cmdFileName"), True)
                Dim TempHardwareFN As String = mSaveFolder + "/hardwareSettings.txt"
                My.Computer.FileSystem.CopyFile(INIFileName, TempHardwareFN, True)
                My.Computer.FileSystem.WriteAllText(TempHardwareFN, " " + vbCrLf, True)
                My.Computer.FileSystem.WriteAllText(TempHardwareFN, "DeviceType = " + CardModelString + vbCrLf, True)
                My.Computer.FileSystem.WriteAllText(TempHardwareFN, "MaxADCvalue = " + CardMaxValueString + vbCrLf, True)
                My.Computer.FileSystem.WriteAllText(TempHardwareFN, "ComputerName = " + Environment.MachineName + vbCrLf, True)
                My.Computer.FileSystem.WriteAllText(TempHardwareFN, "INIfileName = " + INIFileName + vbCrLf, True)

                ' setup NI board and load DAC waveforms if doing a refreshed scan
                If Int(mCmdDict("updatescanwaveforms")) = 1 Then
                    TempStr = "scan generation and run"
                    If Me.InvokeRequired Then
                        Me.Invoke(Sub()
                                      Me.Text = TempStr
                                  End Sub)
                    Else
                        Me.Text = TempStr
                    End If
                    Dim mImageParms As Dictionary(Of String, String) = ReadIniFile(mSystemINI("tempExtractFolder") +
                                                                                   "/" + mCmdDict("imagedesc"))

                    mNI.SetPhotometryMode(0)
                    Dim NewRanges As Double()
                    ReDim NewRanges(3)
                    NewRanges(0) = CDbl(mImageParms("chanafullscale"))
                    NewRanges(1) = CDbl(mImageParms("chanbfullscale"))
                    mNI.SetInputRangeList(NewRanges)
                    mNI.SetSampleRate(1000000.0 / CDbl(mImageParms("pixelus"))) ' uS to MHz
                    Dim xData As Double() = readBinaryVector(mSystemINI("tempExtractFolder") + "/" + mImageParms("scanpointsx"))
                    Dim yData As Double() = readBinaryVector(mSystemINI("tempExtractFolder") + "/" + mImageParms("scanpointsy"))
                    mNI.LoadOutputWaveformsFromVector(xData, yData, CLng(mCmdDict("numframes")),
                                                      CLng(mImageParms("lagpixels")))
                    My.Computer.FileSystem.CopyFile(mSystemINI("tempExtractFolder") + "/" + mCmdDict("imagedesc"),
                                            mSaveFolder + "/" + mCmdDict("imagedesc"), True)
                    My.Computer.FileSystem.CopyFile(mSystemINI("tempExtractFolder") + "/" + mCmdDict("imagedesc"),
                                            mSystemINI("tempCacheFolder") + "/" + mCmdDict("imagedesc"), True)
                    ' mNI.SetReturnEndPoint(mImageParms("localip"), mImageParms("returnport"))
                    mNI.SetReturnEndPoint(mCmdDict("returnipaddress"), CInt(mCmdDict("returnport")))
                Else
                    ' do not update scan waveforms
                    If Not mNI.OutputWaveformsLoaded Then
                        TempStr = "ERROR no scans available"
                        If Me.InvokeRequired Then
                            Me.Invoke(Sub()
                                          Me.Text = TempStr
                                      End Sub)
                        Else
                            Me.Text = TempStr
                        End If
                        Exit Sub
                    End If
                    TempStr = "only run"
                    If Me.InvokeRequired Then
                        Me.Invoke(Sub()
                                      Me.Text = TempStr
                                  End Sub)
                    Else
                        Me.Text = TempStr
                    End If
                    My.Computer.FileSystem.CopyFile(mSystemINI("tempCacheFolder") + "/" + mCmdDict("imagedesc"),
                                            mSaveFolder + "/" + mCmdDict("imagedesc"), True)
                End If ' update scan waveforms
                mNI.SetTempFolder(mSaveFolder)
                mNI.SetOutputZipFile(mSystemINI("tempOutputFile"))
                mNI.SetWaitForExtTrig(0)
                mNI.CreateTasks()
                mNI.WriteWaveforms()
                mNI.RunNIBoard(1 = CInt(mCmdDict("returnpositiondata"))) ' False means PMTs and True means return position
            Case Else
                TempStr = "Unknown command: " + mCmdDict("currentcommand")
                If Me.InvokeRequired Then
                    Me.Invoke(Sub()
                                  Me.Text = TempStr
                              End Sub)
                Else
                    Me.Text = TempStr
                End If
                Exit Sub
        End Select
    End Sub

    ' 
    ' GUI and call backs below here
    '

    Private Sub Form1_Load(sender As System.Object, e As System.EventArgs) Handles MyBase.Load
        Dim CmdArgs As String() = Environment.GetCommandLineArgs()
        If CmdArgs.GetUpperBound(0) > 0 Then
            INIFileName = CmdArgs(1) ' use first command line argument provided as parameter file
        Else
            ' no arguments provides so use labWorld default
            INIFileName = "D:\LabWorld\INIs\ToronadoHardware.ini"
        End If

        If Not My.Computer.FileSystem.FileExists(INIFileName) Then
            MsgBox("Missing parameter file """ + INIFileName + """ so program is closing.")
            End
        Else
            Try
                mSystemINI = ReadIniFile(INIFileName)
            Catch ex As Exception
                MsgBox("Cannot read startup parms from " + INIFileName)
                Exit Sub
            End Try
        End If
        If My.Computer.FileSystem.DirectoryExists(mSystemINI("tempExtractFolder")) Then
            My.Computer.FileSystem.DeleteDirectory(mSystemINI("tempExtractFolder"), FileIO.DeleteDirectoryOption.DeleteAllContents)
        End If
        If My.Computer.FileSystem.DirectoryExists(mSystemINI("tempSaveFolder")) Then
            My.Computer.FileSystem.DeleteDirectory(mSystemINI("tempSaveFolder"), FileIO.DeleteDirectoryOption.DeleteAllContents)
        End If
        If My.Computer.FileSystem.DirectoryExists(mSystemINI("tempCacheFolder")) Then
            My.Computer.FileSystem.DeleteDirectory(mSystemINI("tempCacheFolder"), FileIO.DeleteDirectoryOption.DeleteAllContents)
        End If
        If My.Computer.FileSystem.FileExists(mSystemINI("tempInputFile")) Then
            My.Computer.FileSystem.DeleteFile(mSystemINI("tempInputFile"))
        End If
        W = New benTCPlistener(Me, mSystemINI("tempInputFile"), mSystemINI("listenIP"), CInt(mSystemINI("listenPort")))
        W.Start()
        If Len(mSystemINI("NImxDeviceName")) > 0 Then
            mNI = New BenNI6111(Me, mSystemINI("NImxDeviceName"))
            mNI.ZeroGalvos()
            mNI.SetPhaseJitter(CBool(mSystemINI("PhaseJitter")))
            pnlPhaseDither.Visible = CBool(mSystemINI("PhaseJitter"))
            mNI.SetOuterLoopFor5ms(CLng(mSystemINI("5msLoopCounter")))
            CardModelString = mNI.GetCardName
            CardMaxValueString = mNI.GetMaxValue()
            Me.Text = "Finished setting up NI board"
        End If
        mGreenPreAmp = New clsSerialPreAmpControl
        mRedPreAmp = New clsSerialPreAmpControl
        If CInt(mSystemINI("UseSerialPreAmpControl")) = 1 Then
            If Len(mSystemINI("GreenComPort")) > 0 Then
                mGreenPreAmp.StartPort(mSystemINI("GreenComPort"), "Green")
                mGreenPreAmp.SetRasterDefault()
            End If
            If Len(mSystemINI("RedComPort")) > 0 Then
                mRedPreAmp.StartPort(mSystemINI("RedComPort"), "Red")
                mRedPreAmp.SetRasterDefault()
            End If
        End If

    End Sub
  
    Private Sub frmRaster_FormClosing(ByVal sender As Object, ByVal e As System.Windows.Forms.FormClosingEventArgs) Handles Me.FormClosing
        TasksBeforeEnd()
    End Sub

    Private Sub TasksBeforeEnd()
        '  CloseShutter()
        ' ChangeMonitorState(True)
        Application.DoEvents()
        End
    End Sub

    Friend Sub ClearTitle(Optional ByVal ErrorMsg As String = "")
        SW.Stop()
        Dim TempStr As String
        If ErrorMsg <> "" Then
            TempStr = ErrorMsg
        Else
            TempStr = "Raster idle (last " + SW.ElapsedMilliseconds.ToString + " ms)"
        End If
        If Me.InvokeRequired Then
            Me.Invoke(Sub()
                          Me.Text = TempStr
                      End Sub)
        Else
            Me.Text = TempStr
        End If
    End Sub

    Private Sub cmdOpenShutter_Click(ByVal sender As System.Object, ByVal e As System.EventArgs) Handles cmdOpenShutter.Click
        mNI.SetDigitalBit(0, 1)
    End Sub

    Private Sub cmdCloseShutter_Click(ByVal sender As System.Object, ByVal e As System.EventArgs) Handles cmdCloseShutter.Click
        mNI.SetDigitalBit(0, 0)
    End Sub

    Private Function ReadIniFile(ByVal filename As String) As Dictionary(Of String, String)
        ' from vbnotebookfor.net/2007/09/25/3-handy
        Dim IniContents As New Dictionary(Of String, String)
        Dim TempStr As String()
        If Not IO.File.Exists(filename) Then
            Return IniContents
        End If
        Using INIFileParser As FileIO.TextFieldParser = My.Computer.FileSystem.OpenTextFieldParser(filename, "=")
            Dim CurrentLine() As String
            With INIFileParser
                .TrimWhiteSpace = True
                Do While Not INIFileParser.EndOfData
                    CurrentLine = .ReadFields()
                    If CurrentLine(0).Length > 0 Then
                        Try
                            Select Case CurrentLine(0).Substring(0, 1)
                                Case ";"
                                    'ignore comments
                                Case "["
                                    'section header
                                    ' IniContents.Add(New String() {CurrentLine(0), CurrentLine(0)})
                                Case Else
                                    TempStr = CurrentLine(1).Split(";")
                                    '   MsgBox("Here: " + CurrentLine(0))
                                    IniContents.Add(CurrentLine(0), TempStr(0).Trim)
                            End Select
                        Catch
                        End Try
                    End If
                Loop
            End With
        End Using
        Return IniContents
    End Function

    Private Function readBinaryVector(ByVal vecName) As Double()
        If My.Computer.FileSystem.FileExists(vecName) Then
            Dim MyReader As New BinaryReader(File.Open(vecName, FileMode.Open, FileAccess.Read))
            Dim arrayLength As Long = My.Computer.FileSystem.GetFileInfo(vecName).Length / 8
            Dim newVec As Double()
            ReDim newVec(arrayLength)
            For ii As Long = 0 To arrayLength - 1
                newVec(ii) = MyReader.ReadDouble()
            Next
            MyReader.Close()
            Return newVec
        Else
            MsgBox("Cannot find requested binary file: " + vecName)
            Return Nothing
        End If
    End Function



 
End Class
